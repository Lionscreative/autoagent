"""
Harbor agent that runs the RobotSpeed section-writer eval harness.

Architecture:
1. Reads the task instruction (a JSON with {"fixture_id": "..."}) from
   /task/instruction.md
2. Calls scripts/section-writer-eval.ts in the RobotSpeed repo via
   `npx tsx ... <fixture_id> --json`
3. Parses the JSON output (stdout) containing scores + per-dim details
4. Writes /tmp/eval_results.json in the Harbor Docker container so the
   verifier inside the container can compute the reward

Unlike agent_sophie.py, this agent does NOT run a host-side judge: all
scoring (factuality, SEO, specificity, originality) already happens
inside the TS script via Gemini Flash + OpenAI embeddings + cosine math.
The Python side is just a thin bridge.

Before any run (per iteration), agent_writer.py ALSO calls
scripts/validate-prompts.ts to enforce the guardrails the meta-agent
must respect (link-seller ternary, prompt length floor, critical markers,
judge.ts SHA256 pin). Non-zero exit = iteration aborted.

Critical: this agent writes NOTHING to the RobotSpeed DB. All Bedrock
calls hit the writer in memory only. Cost per task: ~$0.03.

Run:
  cd /Users/eliott/Documents/GitHub/autoagent
  set -a && source .env && set +a
  rm -rf jobs/writer-baseline && mkdir -p jobs/writer-baseline
  .venv/bin/harbor run -p tasks-writer/ -n 1 \\
    --agent-import-path agent_writer:AutoAgent -o jobs \\
    --job-name writer-baseline --env-file .env -y
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import time
from datetime import datetime, timezone

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


# ============================================================================
# CONFIG
# ============================================================================

ROBOTSPEED_REPO = os.environ.get(
    "ROBOTSPEED_REPO",
    "/Users/eliott/Documents/GitHub/RobotSpeed",
)

BRIDGE_SCRIPT = "scripts/section-writer-eval.ts"
VALIDATE_SCRIPT = "scripts/validate-prompts.ts"

# writeSection on Sonnet 4.5 + 3 judges + embeddings + overhead
EVAL_TIMEOUT_SEC = 180

# Pinned SHA256 of eval/judge.ts — prevents the meta-agent from tampering
# with the scoring rubric to inflate its own scores. Computed and pinned
# once at Phase 2 start, updated manually only on intentional judge edits.
# An empty string disables the check (NOT recommended for real runs).
JUDGE_SHA256_PIN = os.environ.get("JUDGE_SHA256_PIN", "")


# ============================================================================
# BRIDGE HELPERS
# ============================================================================

def _env_for_subprocess() -> dict:
    """Build the env for the npx tsx subprocess.

    Inherits the parent env for PATH etc, but SCRUBS autoagent-specific
    vars that would leak into RobotSpeed's code and break it:

    - OPENAI_BASE_URL  — autoagent/.env sets this to the OpenAI Agents SDK
      proxy which doesn't support /v1/embeddings. If it leaks, @ai-sdk/openai
      routes embedding calls to the proxy, gets HTML back, and fails with
      "Invalid JSON response". (Discovered the hard way during Phase 2
      smoke test — the dry-run worked but real runs crashed at originality.)
    - OPENAI_ORGANIZATION / OPENAI_ORG_ID — same class of risk.
    - OPENAI_AGENTS_DISABLE_TRACING — benign but unnecessary.

    The RobotSpeed eval script loads its own .env.local via dotenv, which
    supplies the real OPENAI_API_KEY / BEDROCK_API_KEY / DATAFORSEO_* /
    OPENROUTER_API_KEY / SUPABASE_* vars.
    """
    env = {**os.environ}

    # Scrub autoagent-specific OpenAI overrides so the RobotSpeed TS code
    # falls back to its own .env.local and hits api.openai.com directly.
    #
    # Critical caveat: autoagent's .env points OpenAI at MiniMax via
    #   OPENAI_BASE_URL=https://api.minimax.io/v1
    #   OPENAI_API_KEY=sk-cp-... (a MiniMax key in OpenAI format)
    # If any of these leak into RobotSpeed's TS subprocess, embeddings
    # get routed to MiniMax which (a) doesn't support /v1/embeddings and
    # (b) rejects the key with "Incorrect API key provided".
    #
    # We scrub OPENAI_API_KEY too because dotenv.config() does NOT override
    # existing env vars by default — so even though RobotSpeed's .env.local
    # has the real OPENAI_API_KEY, the leaked autoagent one would win.
    for leaky_var in (
        "OPENAI_BASE_URL",
        "OPENAI_API_BASE",
        "OPENAI_API_KEY",            # must scrub: autoagent overrides with MiniMax key
        "OPENAI_ORGANIZATION",
        "OPENAI_ORG_ID",
        "OPENAI_AGENTS_DISABLE_TRACING",
    ):
        env.pop(leaky_var, None)

    if JUDGE_SHA256_PIN:
        env["JUDGE_SHA256"] = JUDGE_SHA256_PIN
    return env


async def _run_subprocess(args: list[str], timeout: int) -> tuple[int, str, str]:
    """Run `npx tsx <args>` in the RobotSpeed repo and return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "npx",
        "tsx",
        *args,
        cwd=ROBOTSPEED_REPO,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_env_for_subprocess(),
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"Subprocess timed out after {timeout}s: {' '.join(args)}")
    return (
        proc.returncode or 0,
        stdout_b.decode("utf-8", errors="replace"),
        stderr_b.decode("utf-8", errors="replace"),
    )


async def validate_prompts() -> tuple[bool, str]:
    """Run scripts/validate-prompts.ts. Returns (ok, message).

    If the guards fail, this iteration MUST be aborted — do NOT score anything.
    """
    try:
        code, stdout, stderr = await _run_subprocess([VALIDATE_SCRIPT], timeout=30)
    except TimeoutError as e:
        return False, f"validate-prompts timed out: {e}"

    if code == 0:
        return True, "validate-prompts: OK"
    return False, f"validate-prompts EXIT {code}\n{stdout}\n{stderr}"


def _extract_json_from_stdout(text: str) -> dict | None:
    """Find the last JSON object line in stdout. Tolerant to prefix junk
    (e.g. leaked AI SDK warnings)."""
    stripped = text.strip()
    # Try whole-text parse first
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    # Walk lines from the end looking for a full JSON object
    for line in reversed(stripped.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    # Last resort: regex the biggest {...} blob
    matches = re.findall(r"\{.*\}", stripped, re.DOTALL)
    if matches:
        try:
            return json.loads(matches[-1])
        except json.JSONDecodeError:
            pass
    return None


async def call_section_writer_eval(fixture_id: str) -> dict:
    """Invoke scripts/section-writer-eval.ts --json for the given fixture.

    Returns the parsed JSON payload (the top-level object with 'success',
    'scored_count', 'results', etc). Raises on non-zero exit or parse failure.

    If the payload indicates failure (success=false), this function injects
    the last 2000 chars of stderr into payload['error'] so the caller gets
    a meaningful error message instead of "unknown".
    """
    code, stdout, stderr = await _run_subprocess(
        [BRIDGE_SCRIPT, fixture_id, "--json"],
        timeout=EVAL_TIMEOUT_SEC,
    )

    parsed = _extract_json_from_stdout(stdout)

    if code != 0:
        if parsed is not None:
            # Surface stderr tail as the error so callers can diagnose
            if not parsed.get("success"):
                existing = parsed.get("error") or ""
                parsed["error"] = f"{existing}\nSTDERR (last 2000):\n{stderr[-2000:]}"
            return parsed
        raise RuntimeError(
            f"section-writer-eval exit {code}\n"
            f"STDERR (last 2000): {stderr[-2000:]}\n"
            f"STDOUT (last 500): {stdout[-500:]}"
        )

    if parsed is None:
        raise RuntimeError(
            f"section-writer-eval returned no parseable JSON (exit {code})\n"
            f"STDERR (last 2000): {stderr[-2000:]}\n"
            f"STDOUT (last 1000): {stdout[-1000:]}"
        )

    # If parsed but success=false, surface stderr for diagnosis
    if not parsed.get("success") and not parsed.get("error"):
        parsed["error"] = f"STDERR (last 2000):\n{stderr[-2000:]}"

    return parsed


# ============================================================================
# HARBOR AGENT
# ============================================================================

class AutoAgent(BaseAgent):
    """Harbor agent that runs the section-writer eval harness in isolation
    and writes the composite score into the verifier's JSON file."""

    SUPPORTS_ATIF = True

    @staticmethod
    def name() -> str:
        return "writer-eval"

    def version(self) -> str | None:
        return "0.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        pass

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        t0 = time.time()

        try:
            # 1. Parse instruction (expected: {"fixture_id": "..."})
            try:
                spec = json.loads(instruction.strip())
            except json.JSONDecodeError as e:
                raise ValueError(f"Instruction must be valid JSON with fixture_id: {e}")

            fixture_id = spec.get("fixture_id")
            if not fixture_id:
                raise ValueError("Instruction JSON must include 'fixture_id'")

            print(f"[writer-eval] Evaluating fixture: {fixture_id}")

            # 2. Validate prompt guards BEFORE running the expensive writer
            print("[writer-eval] Running validate-prompts...")
            ok, msg = await validate_prompts()
            print(f"[writer-eval] {msg}")
            if not ok:
                # Guardrail violated. Score 0 and abort.
                eval_data = {
                    "success": False,
                    "error": f"validate-prompts failed: {msg}",
                    "fixture_id": fixture_id,
                    "aborted": True,
                    "scores": None,
                }
                await self._write_eval_results(environment, eval_data)
                await self._write_trajectory(
                    fixture_id=fixture_id,
                    duration_ms=int((time.time() - t0) * 1000),
                    composite=0.0,
                    eval_data=eval_data,
                    validate_ok=False,
                )
                return

            # 3. Call the TS eval harness
            print(f"[writer-eval] Calling {BRIDGE_SCRIPT}...")
            payload = await call_section_writer_eval(fixture_id)

            if not payload.get("success"):
                err = payload.get("error", "unknown error")
                print(f"[writer-eval] Eval FAILED: {err}")
                eval_data = {
                    "success": False,
                    "error": err,
                    "fixture_id": fixture_id,
                    "scores": None,
                }
                composite = 0.0
            else:
                results = payload.get("results") or []
                if not results:
                    raise RuntimeError("payload.success=true but results array is empty")
                result = results[0]
                scores = result.get("scores") or {}
                composite = float(scores.get("composite", 0.0))

                print(
                    f"[writer-eval] composite={composite:.2f} "
                    f"(raw_geomean={scores.get('raw_geometric_mean', 0):.2f}) "
                    f"winston={scores.get('winston', 0)} "
                    f"fact={scores.get('factuality', 0)} "
                    f"orig={scores.get('originality', 0)} "
                    f"seo={scores.get('seo', 0)} "
                    f"spec={scores.get('specificity', 0)} "
                    f"floor={scores.get('floor_triggered', False)}"
                )

                eval_data = {
                    "success": True,
                    "fixture_id": fixture_id,
                    "scores": scores,
                    "details": result.get("details"),
                    "costs": result.get("costs"),
                    "latency": result.get("latency"),
                    "section_word_count": result.get("section_word_count"),
                    "section_html_preview": (result.get("section_html") or "")[:500],
                }

            # 4. Write eval_results.json into the verifier's Docker container
            await self._write_eval_results(environment, eval_data)

            # 5. Write trajectory for Harbor
            duration_ms = int((time.time() - t0) * 1000)
            await self._write_trajectory(
                fixture_id=fixture_id,
                duration_ms=duration_ms,
                composite=composite,
                eval_data=eval_data,
                validate_ok=True,
            )

            print(f"[writer-eval] Done in {duration_ms}ms — composite {composite:.2f}")

        except Exception as e:
            print(f"[writer-eval] FATAL: {e}")
            await self._write_trajectory_error(str(e))
            # Still write eval_results so the verifier scores it as 0
            try:
                fail_data = {
                    "success": False,
                    "error": str(e),
                    "scores": None,
                }
                await self._write_eval_results(environment, fail_data)
            except Exception:
                pass
            raise

    # ------------------------------------------------------------------------

    async def _write_eval_results(self, environment: BaseEnvironment, data: dict) -> None:
        """Write the eval payload into /tmp/eval_results.json inside the verifier
        Docker container (base64 round-trip to survive shell quoting)."""
        raw = json.dumps(data, ensure_ascii=False)
        encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        await environment.exec(
            command=f"echo '{encoded}' | base64 -d > /tmp/eval_results.json",
            timeout_sec=30,
        )

    async def _write_trajectory(
        self,
        fixture_id: str,
        duration_ms: int,
        composite: float,
        eval_data: dict,
        validate_ok: bool,
    ) -> None:
        scores = (eval_data or {}).get("scores") or {}
        costs = (eval_data or {}).get("costs") or {}
        atif = {
            "schema_version": "ATIF-v1.6",
            "session_id": f"writer-eval-{int(time.time())}",
            "agent": {
                "name": "writer-eval",
                "version": "0.1.0",
                "model_name": "claude-sonnet-4-5",
            },
            "steps": [
                {
                    "step_id": 1,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "agent",
                    "message": f"validate-prompts {'OK' if validate_ok else 'FAILED'}",
                },
                {
                    "step_id": 2,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "agent",
                    "message": f"writeSection({fixture_id})",
                },
                {
                    "step_id": 3,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "agent",
                    "message": (
                        f"composite={composite:.2f} | "
                        f"fact={scores.get('factuality', 0)} "
                        f"orig={scores.get('originality', 0)} "
                        f"seo={scores.get('seo', 0)} "
                        f"spec={scores.get('specificity', 0)}"
                    ),
                },
            ],
            "final_metrics": {
                "total_cost_usd": float(costs.get("total_usd", 0) or 0),
                "total_steps": 3,
                "extra": {
                    "duration_ms": duration_ms,
                    "composite": composite,
                    "raw_geometric_mean": scores.get("raw_geometric_mean", 0),
                    "floor_triggered": scores.get("floor_triggered", False),
                    "validate_ok": validate_ok,
                    "success": eval_data.get("success", False),
                },
            },
        }
        traj_path = self.logs_dir / "trajectory.json"
        traj_path.write_text(json.dumps(atif, indent=2, ensure_ascii=False))

    async def _write_trajectory_error(self, err: str) -> None:
        traj_path = self.logs_dir / "trajectory.json"
        traj_path.write_text(
            json.dumps(
                {
                    "schema_version": "ATIF-v1.6",
                    "session_id": "error",
                    "agent": {"name": "writer-eval", "version": "0.1.0"},
                    "steps": [
                        {
                            "step_id": 1,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "source": "agent",
                            "message": f"FATAL: {err}",
                        }
                    ],
                    "final_metrics": {"extra": {"error": err}},
                },
                indent=2,
            )
        )


__all__ = ["AutoAgent"]
