"""
Harbor agent that tests Sophie (RobotSpeed inbound agent) cold email composer.

Architecture:
1. Reads the task instruction (a prospect JSON) from /task/instruction.md
2. Calls Sophie's composeEmail() via `npx tsx scripts/sophie-eval-compose.ts` in the RobotSpeed repo
3. Writes the resulting email to /tmp/eval_results.json for the verifier to score

Critical: This agent runs Sophie in ISOLATION from production:
  - No DB writes
  - No Gmail sends
  - No conversation creation in agent_conversations
  - Only calls the pure composeEmail() function with a mocked QualificationResult

The meta-agent (running program-sophie.md) will modify files in
/Users/eliott/Documents/GitHub/RobotSpeed/libs/agent-inbound/ between runs and
re-invoke the benchmark to measure improvement.

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

    if proc.returncode != 0:
        # Bridge script always writes JSON to stdout even on error, try to parse first
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            raise RuntimeError(
                f"Sophie bridge exit code {proc.returncode}\n"
                f"STDERR: {stderr[:500]}\n"
                f"STDOUT: {stdout[:500]}"
            )

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Sophie bridge returned invalid JSON: {e}\n"
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
                eval_data = {
                    "success": True,
                    "prospect": prospect,
                    "email": email,
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
