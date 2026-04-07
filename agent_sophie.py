"""
Harbor agent that tests Sophie (RobotSpeed inbound agent) cold email composer.

Architecture:
1. Reads the task instruction (a prospect JSON) from /task/instruction.md
2. Calls Sophie's composeEmail() via `npx tsx scripts/sophie-eval-compose.ts` in the RobotSpeed repo
3. Runs the persona judge ON THE HOST (where GROQ_API_KEY / EVAL_PROXY_SECRET are set)
   and embeds the judge results into /tmp/eval_results.json
4. The verifier inside the Docker container reads both the email + pre-computed
   judge results and computes the final reward

This architecture is necessary because Harbor's verifier container doesn't have
access to the host's env vars (GROQ_API_KEY), so the judge call MUST happen
on the host side where the keys live.

Critical: This agent runs Sophie in ISOLATION from production:
  - No DB writes
  - No Gmail sends
  - No conversation creation in agent_conversations
  - Only calls the pure composeEmail() function with a mocked QualificationResult

Run:
  cd /Users/eliott/Documents/GitHub/autoagent
  set -a && source .env && set +a
  rm -rf jobs/sophie-baseline && mkdir -p jobs/sophie-baseline
  .venv/bin/harbor run -p tasks-sophie/ -n 1 \
    --agent-import-path agent_sophie:AutoAgent -o jobs \
    --job-name sophie-baseline --env-file .env -y
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


# ============================================================================
# CONFIG
# ============================================================================

# Path to the RobotSpeed repo on the host machine.
# The bridge TS script lives at scripts/sophie-eval-compose.ts inside this repo.
ROBOTSPEED_REPO = os.environ.get(
    "ROBOTSPEED_REPO",
    "/Users/eliott/Documents/GitHub/RobotSpeed",
)

# Bridge command: npx tsx is already set up in the RobotSpeed repo.
BRIDGE_SCRIPT = "scripts/sophie-eval-compose.ts"

# Timeout for a single composeEmail call (MiniMax can be slow on retries).
COMPOSE_TIMEOUT_SEC = 120


# ============================================================================
# SOPHIE BRIDGE CLIENT
# ============================================================================

async def call_sophie_compose(prospect: dict) -> dict:
    """Invoke scripts/sophie-eval-compose.ts via subprocess, passing prospect JSON on stdin.

    Returns the parsed JSON output. Raises on non-zero exit or parse failure.
    """
    prospect_json = json.dumps(prospect)

    proc = await asyncio.create_subprocess_exec(
        "npx",
        "tsx",
        BRIDGE_SCRIPT,
        cwd=ROBOTSPEED_REPO,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ},  # inherit parent env (MINIMAX_TOKEN_PLAN_KEY, GROQ_API_KEY, etc.)
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(prospect_json.encode()),
            timeout=COMPOSE_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"Sophie compose timed out after {COMPOSE_TIMEOUT_SEC}s")

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")

    def extract_json(text: str) -> dict | None:
        """Find the LAST valid JSON object in stdout.
        Some imports (AI SDK warnings) may print junk before our JSON.
        """
        stripped = text.strip()
        # Try parsing the whole thing first
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
        # Walk lines from the end looking for a complete JSON object
        for line in reversed(stripped.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        # Last resort: find the last {...} blob
        import re as _re
        matches = _re.findall(r'\{.*\}', stripped, _re.DOTALL)
        if matches:
            try:
                return json.loads(matches[-1])
            except json.JSONDecodeError:
                pass
        return None

    if proc.returncode != 0:
        parsed = extract_json(stdout)
        if parsed is not None:
            return parsed
        raise RuntimeError(
            f"Sophie bridge exit code {proc.returncode}\n"
            f"STDERR: {stderr[:500]}\n"
            f"STDOUT: {stdout[:500]}"
        )

    parsed = extract_json(stdout)
    if parsed is not None:
        return parsed
    raise RuntimeError(
        f"Sophie bridge returned no parseable JSON\n"
        f"STDOUT (first 1000 chars): {stdout[:1000]}"
    )


# ============================================================================
# HARBOR AGENT
# ============================================================================

class AutoAgent(BaseAgent):
    """Harbor agent that runs Sophie's composeEmail in isolation and scores the output."""

    SUPPORTS_ATIF = True

    @staticmethod
    def name() -> str:
        return "sophie-eval"

    def version(self) -> str | None:
        return "0.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        pass

    async def _run_host_judge(self, email: dict, personas: list[str]) -> dict:
        """Run the persona judge on the host (has GROQ_API_KEY / EVAL_PROXY_SECRET).
        Returns {avg_score: float, persona_scores: [...], details: [...]}.

        Tries Groq direct first; falls back to the Vercel proxy if Groq is
        geo-blocked (common on local dev Macs).
        """
        import httpx

        JUDGE_PROMPT_TEMPLATE = """Tu es une vraie personne qui reçoit des cold emails commerciaux. Voici ton profil:

PROFIL:
{persona}

CONTEXTE:
- Tu reçois 20 à 50 cold emails par semaine.
- 99% d'entre eux finissent à la corbeille en 3 secondes.
- Tu réponds à MOINS DE 1 sur 30.
- Tu détestes les emails génériques, les flatteries creuses, les "j'ai regardé votre site" non-prouvés.
- Tu apprécies: une observation ULTRA spécifique sur ton business, une vraie question qui montre qu'on te comprend, de la valeur gratuite avant toute demande.

EMAIL REÇU:
Sujet: {subject}
Corps:
{body}

DEFAULT: would_reply = false. Trust signals = 2/10. Feels personal = 1/10.

Pour considérer would_reply = true, l'email DOIT avoir AU MOINS UN des critères suivants:
1. Mentionne quelque chose d'ULTRA spécifique sur le business (pas générique)
2. Pose une VRAIE question à laquelle tu as envie de répondre (pas "ça vous intéresse ?")
3. Apporte de la valeur AVANT de demander quoi que ce soit

Sois IMPITOYABLE. Répondre yes par défaut c'est ce que font les juges LLMs sycophantes.

Réponds STRICTEMENT en JSON:
{{
  "would_reply": true ou false,
  "reply_likelihood_pct": 0 à 100,
  "feels_personal_to_me": 0 à 10,
  "trust_signals": 0 à 10,
  "feels_like_ai_0_to_10": 0 à 10,
  "deal_breaker": "ce qui t'a fait delete (ou null)",
  "what_worked": "ce qui a marché (ou null)"
}}

Réponds UNIQUEMENT avec le JSON, sans markdown."""

        subject = email.get("subject", "") or ""
        body = email.get("body_text", "") or ""

        eval_proxy_url = os.environ.get(
            "EVAL_PROXY_URL",
            "https://www.robot-speed.com/api/admin/eval/llm-judge",
        )
        eval_proxy_secret = os.environ.get("EVAL_PROXY_SECRET", "").strip().strip('"').strip("'")
        groq_api_key = os.environ.get("GROQ_API_KEY", "").strip().strip('"').strip("'")

        persona_scores = []
        details = []

        async with httpx.AsyncClient(timeout=30) as client:
            for i, persona in enumerate(personas):
                prompt = JUDGE_PROMPT_TEMPLATE.format(
                    persona=persona,
                    subject=subject,
                    body=body,
                )
                raw: str | None = None

                # Try Groq direct first
                if groq_api_key:
                    try:
                        resp = await client.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {groq_api_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": "llama-3.3-70b-versatile",
                                "messages": [{"role": "user", "content": prompt}],
                                "temperature": 0.2,
                                "max_tokens": 400,
                                "response_format": {"type": "json_object"},
                            },
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            raw = data["choices"][0]["message"]["content"]
                        else:
                            err_body = resp.text[:200]
                            if resp.status_code == 403 or "access denied" in err_body.lower():
                                pass  # geo-blocked, fall through to proxy
                            else:
                                details.append(f"JUDGE {i+1}: Groq error {resp.status_code}: {err_body}")
                    except Exception as direct_err:
                        details.append(f"JUDGE {i+1}: Groq direct failed ({direct_err})")

                # Fallback: Vercel proxy
                if raw is None and eval_proxy_secret:
                    try:
                        resp = await client.post(
                            eval_proxy_url,
                            headers={
                                "Content-Type": "application/json",
                                "X-Eval-Secret": eval_proxy_secret,
                            },
                            json={
                                "prompt": prompt,
                                "model": "llama-3.3-70b-versatile",
                                "temperature": 0.2,
                                "max_tokens": 400,
                            },
                        )
                        if resp.status_code == 200:
                            raw = resp.json().get("content", "")
                            # Strip markdown fences if present
                            import re as _re
                            raw = _re.sub(r'^```(?:json)?\s*', '', raw.strip())
                            raw = _re.sub(r'\s*```$', '', raw.strip())
                        else:
                            details.append(f"JUDGE {i+1}: Proxy error {resp.status_code}: {resp.text[:200]}")
                    except Exception as proxy_err:
                        details.append(f"JUDGE {i+1}: Proxy failed ({proxy_err})")

                if raw is None:
                    details.append(f"JUDGE {i+1}: No response, scoring 0")
                    persona_scores.append(0.0)
                    continue

                try:
                    judgment = json.loads(raw)
                except json.JSONDecodeError as e:
                    details.append(f"JUDGE {i+1}: Invalid JSON: {e} — raw: {raw[:200]}")
                    persona_scores.append(0.0)
                    continue

                would_reply = bool(judgment.get("would_reply", False))
                feels_personal = float(judgment.get("feels_personal_to_me", 0) or 0)
                trust = float(judgment.get("trust_signals", 0) or 0)
                feels_ai = float(judgment.get("feels_like_ai_0_to_10", 10) or 10)

                persona_score = (
                    (2.0 if would_reply else 0.0)
                    + (feels_personal / 10.0 * 1.5)
                    + (trust / 10.0 * 1.0)
                    + ((10.0 - feels_ai) / 10.0 * 0.5)
                )
                persona_scores.append(persona_score)
                deal = str(judgment.get("deal_breaker") or "—")[:150]
                worked = str(judgment.get("what_worked") or "—")[:150]
                details.append(
                    f"JUDGE {i+1}: reply={would_reply} personal={feels_personal:.0f}/10 "
                    f"trust={trust:.0f}/10 ai-feel={feels_ai:.0f}/10 → {persona_score:.2f}/5"
                )
                details.append(f"  deal_breaker: {deal}")
                details.append(f"  what_worked: {worked}")

        avg_score = sum(persona_scores) / len(persona_scores) if persona_scores else 0.0
        return {
            "avg_score": avg_score,
            "persona_scores": persona_scores,
            "details": details,
        }

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        t0 = time.time()

        try:
            # 1. Parse instruction — should be a JSON prospect spec
            try:
                prospect = json.loads(instruction.strip())
            except json.JSONDecodeError as e:
                raise ValueError(f"Instruction must be valid JSON prospect: {e}")

            # 2. Call Sophie's composer via the TS bridge
            print(
                f"[sophie-eval] Composing email for {prospect.get('contact_email', '?')} "
                f"(language={prospect.get('language')}, type={prospect.get('email_type')})"
            )
            result = await call_sophie_compose(prospect)

            if not result.get("success"):
                err = result.get("error", "unknown error")
                print(f"[sophie-eval] Compose FAILED: {err}")
                # Still write eval_results.json so the verifier can score it as a hard failure
                eval_data = {
                    "success": False,
                    "error": err,
                    "prospect": prospect,
                    "email": None,
                }
            else:
                email = result["email"]
                print(
                    f"[sophie-eval] Composed: subject='{email['subject']}' "
                    f"({len(email['body_text'].split())} words, "
                    f"${email.get('cost_usd', 0):.5f})"
                )

                # 2b. Run the persona judge ON THE HOST (Docker verifier has no API keys)
                # Personas come from the prospect spec under "_personas" (added by task instruction)
                judge_results = None
                personas = prospect.get("_personas") or []
                if personas:
                    try:
                        judge_results = await self._run_host_judge(email, personas)
                        print(f"[sophie-eval] Judge avg: {judge_results.get('avg_score', 0):.2f}/5")
                    except Exception as judge_err:
                        print(f"[sophie-eval] Judge FAILED: {judge_err}")
                        judge_results = {"error": str(judge_err)}

                eval_data = {
                    "success": True,
                    "prospect": prospect,
                    "email": email,
                    "judge_results": judge_results,
                }

            # 3. Write eval results to /tmp/eval_results.json in the Docker container
            eval_json = json.dumps(eval_data, ensure_ascii=False)
            encoded = base64.b64encode(eval_json.encode("utf-8")).decode("ascii")
            await environment.exec(
                command=f"echo '{encoded}' | base64 -d > /tmp/eval_results.json",
                timeout_sec=5,
            )

            # 4. Write trajectory for Harbor
            duration_ms = int((time.time() - t0) * 1000)
            atif = {
                "schema_version": "ATIF-v1.6",
                "session_id": f"sophie-eval-{int(time.time())}",
                "agent": {
                    "name": "sophie-eval",
                    "version": "0.1.0",
                    "model_name": "minimax-m2.7",
                },
                "steps": [
                    {
                        "step_id": 1,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "agent",
                        "message": f"composeEmail({prospect.get('email_type', '?')})",
                    },
                    {
                        "step_id": 2,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "agent",
                        "message": (
                            result["email"]["subject"]
                            if result.get("success")
                            else f"ERROR: {result.get('error', 'unknown')}"
                        ),
                    },
                ],
                "final_metrics": {
                    "total_prompt_tokens": (
                        result["email"].get("tokens_used", {}).get("input", 0)
                        if result.get("success") else 0
                    ),
                    "total_completion_tokens": (
                        result["email"].get("tokens_used", {}).get("output", 0)
                        if result.get("success") else 0
                    ),
                    "total_cost_usd": (
                        result["email"].get("cost_usd", 0)
                        if result.get("success") else 0
                    ),
                    "total_steps": 2,
                    "extra": {
                        "duration_ms": duration_ms,
                        "success": result.get("success", False),
                    },
                },
            }

            traj_path = self.logs_dir / "trajectory.json"
            traj_path.write_text(json.dumps(atif, indent=2, ensure_ascii=False))

            print(f"[sophie-eval] Done in {duration_ms}ms")

        except Exception as e:
            print(f"[sophie-eval] FATAL: {e}")
            traj_path = self.logs_dir / "trajectory.json"
            traj_path.write_text(
                json.dumps(
                    {
                        "schema_version": "ATIF-v1.6",
                        "session_id": "error",
                        "agent": {"name": "sophie-eval", "version": "0.1.0"},
                        "steps": [
                            {
                                "step_id": 1,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "source": "agent",
                                "message": f"FATAL: {e}",
                            }
                        ],
                        "final_metrics": {"extra": {"error": str(e)}},
                    },
                    indent=2,
                )
            )
            # Still write an eval_results.json so the verifier scores it 0
            try:
                fail_data = json.dumps({"success": False, "error": str(e), "email": None})
                encoded = base64.b64encode(fail_data.encode()).decode()
                await environment.exec(
                    command=f"echo '{encoded}' | base64 -d > /tmp/eval_results.json",
                    timeout_sec=5,
                )
            except Exception:
                pass
            raise


__all__ = ["AutoAgent"]
