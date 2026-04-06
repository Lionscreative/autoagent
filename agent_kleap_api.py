"""
Harbor agent that tests the REAL Kleap production agent.

Instead of running a local AI model, this agent:
1. Creates a real app on Kleap (via API with service role auth)
2. Sends the benchmark prompt to our real AI agent
3. Waits for the AI to finish building
4. Downloads the resulting files from Supabase
5. Uploads them to the Docker container for build verification + scoring

This tests our actual production system (real prompt, real tools, real model).

Run:
  docker build -f Dockerfile.kleap -t autoagent-base .
  set -a && source .env && set +a
  uv run harbor run -p tasks/ --agent-import-path agent_kleap_api:AutoAgent -o jobs
"""

from __future__ import annotations

import base64
import json
import os
import time
from datetime import datetime, timezone

import httpx
from supabase import create_client as create_supabase_client

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


# ============================================================================
# CONFIG
# ============================================================================

KLEAP_API_URL = os.environ.get("KLEAP_API_URL", "https://kleap.co")
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
EVAL_USER_ID = os.environ.get("EVAL_USER_ID", "7aafd925-36b3-440f-8bfd-e517837d885f")


# ============================================================================
# KLEAP API CLIENT (uses service role key + X-Eval-User-Id)
# ============================================================================

class KleapEvalClient:
    """Client that talks to the real Kleap API using service role auth."""

    def __init__(self):
        self._admin_sb = None

    def _headers(self) -> dict[str, str]:
        """Auth headers: service role key + eval user ID."""
        return {
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "X-Eval-User-Id": EVAL_USER_ID,
            "Content-Type": "application/json",
        }

    def _get_admin_sb(self):
        if not self._admin_sb:
            self._admin_sb = create_supabase_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        return self._admin_sb

    async def create_app(self, name: str) -> tuple[int, int]:
        """Create a new app on Kleap. Returns (app_id, chat_id)."""
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{KLEAP_API_URL}/api/create-app",
                json={"name": name},
                headers=self._headers(),
            )
            if resp.status_code != 200:
                raise Exception(f"Create app failed ({resp.status_code}): {resp.text[:500]}")

            data = resp.json()
            if not data.get("success"):
                raise Exception(f"Create app error: {data.get('error', 'unknown')}")

            result = data["result"]
            app_id = result["app"]["id"]
            chat_id = result["chatId"]
            print(f"[eval] Created app '{name}' (id={app_id}, chat_id={chat_id})")
            return app_id, chat_id

    async def send_prompt(self, chat_id: int, prompt: str) -> dict:
        """Send a prompt to our real AI and wait for completion.
        Returns trajectory info."""
        trajectory = {
            "tool_calls": [],
            "text_chunks": [],
            "errors": [],
            "finished": False,
            "finish_reason": None,
        }

        t0 = time.time()

        async with httpx.AsyncClient(timeout=600) as client:
            async with client.stream(
                "POST",
                f"{KLEAP_API_URL}/api/stream/chat",
                json={
                    "chatId": chat_id,
                    "prompt": prompt,
                    "budgetMode": "CONTINUOUS",
                },
                headers=self._headers(),
            ) as stream:
                if stream.status_code != 200:
                    body = await stream.aread()
                    raise Exception(f"Stream failed ({stream.status_code}): {body.decode()[:500]}")

                event_type = None
                async for line in stream.aiter_lines():
                    line = line.strip()

                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                        continue
                    elif line.startswith("data:"):
                        data_str = line[5:].strip()
                    elif line.startswith(":"):
                        continue
                    elif line == "":
                        event_type = None
                        continue
                    else:
                        continue

                    try:
                        data = json.loads(data_str)
                    except (json.JSONDecodeError, TypeError):
                        continue

                    evt = data.get("type", event_type or "")

                    if evt == "data-tool-call":
                        trajectory["tool_calls"].append({
                            "tool": data.get("toolName"),
                            "id": data.get("toolUseId"),
                        })
                    elif evt == "chunk":
                        trajectory["text_chunks"].append(data.get("chunk", ""))
                    elif evt == "error":
                        trajectory["errors"].append(data.get("error", "unknown"))
                    elif evt in ("data-stream-end", "data-stream-complete"):
                        trajectory["finished"] = True
                        trajectory["finish_reason"] = "complete"
                        break
                    elif evt in ("budget-exceeded", "budget-stopped"):
                        trajectory["finished"] = True
                        trajectory["finish_reason"] = "budget"
                        break

        trajectory["duration_ms"] = int((time.time() - t0) * 1000)
        trajectory["n_tool_calls"] = len(trajectory["tool_calls"])
        trajectory["ai_text"] = "".join(trajectory["text_chunks"])

        print(f"[eval] Stream done: {trajectory['n_tool_calls']} tools, "
              f"{trajectory['duration_ms']}ms, finish={trajectory['finish_reason']}")
        return trajectory

    async def get_app_files(self, app_id: int) -> dict[str, str]:
        """Get all files for an app from Supabase."""
        sb = self._get_admin_sb()
        result = sb.table("app_files").select("path, content").eq("app_id", app_id).execute()
        files = {}
        for row in result.data:
            if row.get("content"):
                files[row["path"]] = row["content"]
        print(f"[eval] Got {len(files)} files from app {app_id}")
        return files

    async def cleanup_app(self, app_id: int) -> None:
        """Delete the test app."""
        try:
            sb = self._get_admin_sb()
            sb.table("app_files").delete().eq("app_id", app_id).execute()
            sb.table("chats").delete().eq("app_id", app_id).execute()
            sb.table("apps").delete().eq("id", app_id).execute()
            print(f"[eval] Cleaned up app {app_id}")
        except Exception as e:
            print(f"[eval] Cleanup warning: {e}")


# ============================================================================
# HARBOR AGENT
# ============================================================================

class AutoAgent(BaseAgent):
    """Harbor agent that tests the real Kleap production agent."""

    SUPPORTS_ATIF = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = KleapEvalClient()

    @staticmethod
    def name() -> str:
        return "kleap-eval"

    def version(self) -> str | None:
        return "2.0.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        pass

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        t0 = time.time()
        app_id = None

        try:
            # 1. Create app on real Kleap
            app_name = f"eval-{int(time.time())}"
            app_id, chat_id = await self._client.create_app(app_name)

            # 2. Send benchmark prompt to our REAL AI agent
            trajectory = await self._client.send_prompt(chat_id, instruction)

            # 3. Download resulting files from Supabase
            files = await self._client.get_app_files(app_id)

            # 4. Upload files to Docker container for build verification
            uploaded = 0
            for path, content in files.items():
                # Map to /project/ in container
                if path.startswith("/"):
                    full_path = f"/project{path}"
                else:
                    full_path = f"/project/{path}"

                safe_path = full_path.replace("'", "'\\''")
                encoded = base64.b64encode(content.encode()).decode()
                try:
                    await environment.exec(
                        command=f"mkdir -p $(dirname '{safe_path}') && echo '{encoded}' | base64 -d > '{safe_path}'",
                        timeout_sec=10,
                    )
                    uploaded += 1
                except Exception as e:
                    print(f"[eval] Warning: failed to upload {path}: {e}")

            print(f"[eval] Uploaded {uploaded}/{len(files)} files to container")

            # 5. Write trajectory
            duration_ms = int((time.time() - t0) * 1000)
            atif = {
                "schema_version": "ATIF-v1.6",
                "session_id": f"kleap-eval-{int(time.time())}",
                "agent": {"name": "kleap-eval", "version": "2.0.0", "model_name": "production"},
                "steps": [
                    {"step_id": i + 1, "timestamp": datetime.now(timezone.utc).isoformat(),
                     "source": "agent", "message": f"Tool: {tc['tool']}"}
                    for i, tc in enumerate(trajectory.get("tool_calls", []))
                ] or [{"step_id": 1, "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "agent", "message": "(no output)"}],
                "final_metrics": {
                    "total_steps": trajectory.get("n_tool_calls", 0),
                    "extra": {
                        "duration_ms": duration_ms,
                        "finish_reason": trajectory.get("finish_reason"),
                        "errors": trajectory.get("errors", []),
                        "files_count": len(files),
                    },
                },
            }
            traj_path = self.logs_dir / "trajectory.json"
            traj_path.write_text(json.dumps(atif, indent=2))

            print(f"[eval] Done: {len(files)} files, {trajectory['n_tool_calls']} tools, {duration_ms}ms")

        except Exception as e:
            print(f"[eval] ERROR: {e}")
            traj_path = self.logs_dir / "trajectory.json"
            traj_path.write_text(json.dumps({
                "schema_version": "ATIF-v1.6", "session_id": "error",
                "agent": {"name": "kleap-eval", "version": "2.0.0"},
                "steps": [{"step_id": 1, "timestamp": datetime.now(timezone.utc).isoformat(),
                           "source": "agent", "message": f"ERROR: {e}"}],
                "final_metrics": {"extra": {"error": str(e)}},
            }, indent=2))
            raise

        finally:
            if app_id:
                await self._client.cleanup_app(app_id)


__all__ = ["AutoAgent"]
