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
        """Create a new app on Kleap. Returns (app_id, chat_id).

        The create-app endpoint may return 500 due to sandbox file sync failures,
        but the app + chat + sandbox are already created at that point.
        We handle this by checking Supabase directly if the API fails.
        """
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{KLEAP_API_URL}/api/create-app",
                json={"name": name},
                headers=self._headers(),
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    result = data["result"]
                    app_id = result["app"]["id"]
                    chat_id = result["chatId"]
                    print(f"[eval] Created app '{name}' (id={app_id}, chat_id={chat_id})")
                    return app_id, chat_id

            # API returned error — but the app may still have been created
            # (common case: sandbox created but file sync to DB failed)
            print(f"[eval] create-app returned {resp.status_code}, checking DB...")
            sb = self._get_admin_sb()

            # Check if app was created
            result = sb.table("apps").select("id,sandbox_id").eq("name", name).eq(
                "user_id", EVAL_USER_ID
            ).order("created_at", desc=True).limit(1).execute()

            if not result.data:
                raise Exception(f"Create app failed ({resp.status_code}): {resp.text[:300]}")

            app_id = result.data[0]["id"]

            # Check if chat was created
            chat_result = sb.table("chats").select("id").eq("app_id", app_id).limit(1).execute()
            if not chat_result.data:
                # Create chat manually
                chat_result = sb.table("chats").insert({
                    "app_id": app_id, "user_id": EVAL_USER_ID, "title": "Eval"
                }).select("id").execute()

            chat_id = chat_result.data[0]["id"]
            print(f"[eval] App recovered from DB: id={app_id}, chat_id={chat_id}, "
                  f"sandbox={result.data[0].get('sandbox_id')}")
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
                            "tool": data.get("toolName") or data.get("tool_name") or data.get("name") or "unknown",
                            "id": data.get("toolUseId") or data.get("tool_use_id") or "",
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
        result = sb.table("app_files").select("file_path, content").eq("app_id", app_id).execute()
        files = {}
        for row in result.data:
            if row.get("content") and row.get("file_path"):
                files[row["file_path"]] = row["content"]
        print(f"[eval] Got {len(files)} files from app {app_id}")
        return files

    async def check_preview(self, app_id: int, pages: list[str] | None = None) -> dict:
        """Check the live preview URL — this is what the user actually sees.

        Returns {homepage_ok, pages_ok: {path: bool}, homepage_html, status_codes}.
        """
        sb = self._get_admin_sb()
        r = sb.table("apps").select("sandbox_id, vercel_deployment_url").eq("id", app_id).limit(1).execute()
        r.data = r.data[0] if r.data else None
        preview_url = r.data.get("vercel_deployment_url") if r.data else None

        if not preview_url:
            print("[eval] No preview URL — can't check preview")
            return {"homepage_ok": False, "error": "no preview url"}

        base_url = preview_url.rstrip("/")
        result = {"base_url": base_url, "status_codes": {}, "pages_ok": {}}

        pages_to_check = ["/"] + (pages or [])

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for page in pages_to_check:
                url = f"{base_url}{page}"
                try:
                    resp = await client.get(url)
                    status = resp.status_code
                    result["status_codes"][page] = status
                    ok = status == 200 and len(resp.text) > 100
                    result["pages_ok"][page] = ok

                    if page == "/":
                        result["homepage_ok"] = ok
                        result["homepage_html"] = resp.text[:5000] if ok else ""
                        result["homepage_length"] = len(resp.text)

                    print(f"[eval] Preview {page}: {status} ({len(resp.text)} chars)")
                except Exception as e:
                    result["status_codes"][page] = 0
                    result["pages_ok"][page] = False
                    print(f"[eval] Preview {page}: FAILED ({e})")

        if "/" not in result.get("status_codes", {}):
            result["homepage_ok"] = False

        return result

    async def cleanup_app(self, app_id: int) -> None:
        """Delete the test app and its data."""
        try:
            sb = self._get_admin_sb()
            # Get chat IDs first
            chats = sb.table("chats").select("id").eq("app_id", app_id).execute()
            for chat in chats.data:
                sb.table("messages").delete().eq("chat_id", chat["id"]).execute()
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

            # 3. Check the LIVE PREVIEW (what the user actually sees)
            # Parse instruction for expected pages
            expected_pages = []
            instruction_lower = instruction.lower()
            for page in ["/about", "/contact", "/menu", "/pricing", "/gallery", "/blog", "/services"]:
                page_name = page.strip("/")
                if page_name in instruction_lower:
                    expected_pages.append(page)

            preview = await self._client.check_preview(app_id, expected_pages)

            # 4. Download resulting files from Supabase
            files = await self._client.get_app_files(app_id)

            # 5. Upload files + preview results to Docker container
            uploaded = 0
            for path, content in files.items():
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

            # Write preview results so the test can use them
            preview_json = json.dumps({
                "preview": preview,
                "files": list(files.keys()),
                "tool_calls": trajectory.get("n_tool_calls", 0),
                "duration_ms": trajectory.get("duration_ms", 0),
                "ai_text": trajectory.get("ai_text", "")[:1000],
            })
            preview_encoded = base64.b64encode(preview_json.encode()).decode()
            await environment.exec(
                command=f"echo '{preview_encoded}' | base64 -d > /tmp/eval_results.json",
                timeout_sec=5,
            )

            print(f"[eval] Uploaded {uploaded}/{len(files)} files + preview results")

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
