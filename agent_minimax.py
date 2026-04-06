"""
MiniMax M2.7 agent harness for Kleap web development tasks.
Uses OpenAI Agents SDK with MiniMax's OpenAI-compatible API.

The meta-agent (Claude Code) iterates on this file to improve
the agent's ability to build and fix Next.js websites.

Run all tasks:
  docker build -f Dockerfile.kleap -t autoagent-base .
  set -a && source .env && set +a
  uv run harbor run -p tasks/ --agent-import-path agent_minimax:AutoAgent -o jobs
"""

from __future__ import annotations

import base64
import json
import os
import time
from datetime import datetime, timezone

from agents import Agent, Runner, function_tool
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from agents.items import (
    ItemHelpers,
    MessageOutputItem,
    ReasoningItem,
    ToolCallItem,
    ToolCallOutputItem,
)
from agents.tool import FunctionTool
from agents.usage import Usage
from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from openai import AsyncOpenAI


# ============================================================================
# EDITABLE HARNESS — prompt, tools, agent construction, model config
# ============================================================================

SYSTEM_PROMPT = """You are Kleap, an expert AI web developer that builds complete, professional websites.

Your users are NOT developers. They describe an idea in plain language and expect a stunning, fully working website from their first message. No second chances — the result must be impressive on the first try.

## Your environment
Project at /project: Next.js 15+ (App Router), React 19, TypeScript, Tailwind CSS.

## Your standard of quality
Every website you build must:
- Look like it was designed by a professional agency, not a developer demo
- Have polished visual design: proper spacing, typography hierarchy, color harmony
- Be fully responsive (mobile-first, looks great on all screen sizes)
- Have smooth interactions and hover states
- Include all sections a real website of this type would have
- Use real-sounding placeholder content (not "Lorem ipsum" or "Sample text")
- Pass `npm run build` with zero errors

## Design principles
- Use generous whitespace and padding (py-16+, px-6+)
- Create visual hierarchy with font sizes (text-4xl+ for headings, text-lg for body)
- Apply consistent color scheme derived from the brand/industry
- Add subtle shadows, rounded corners, gradients for depth
- Include hover/focus states on all interactive elements
- Use icons or emoji sparingly for visual interest
- Make the hero section impactful (full viewport, bold headline, clear CTA)
- Add a professional footer with relevant links

## Workflow
1. Understand the user's vision — infer the industry, mood, target audience
2. Plan ALL pages and components before writing any code
3. Create a cohesive design system (colors, fonts, spacing) for the whole site
4. Write all files with complete, production-quality content
5. Run `cd /project && npm run build 2>&1` to verify
6. If build fails: read errors carefully, fix ALL at once, rebuild
7. Never stop until the build passes and every page is complete

## Technical rules
- "use client" for files using useState/useEffect/onClick/onChange
- Tailwind CSS only for styling — no CSS files, no external libraries
- App Router conventions: app/ directory, page.tsx, layout.tsx
- If an import is missing, create the file
- Semantic HTML with proper accessibility (alt texts, aria labels, heading hierarchy)
"""

# MiniMax M2.7 via OpenAI-compatible API
MINIMAX_BASE_URL = os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MODEL_NAME = os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7")
MAX_TURNS = 50


def _get_model() -> OpenAIChatCompletionsModel:
    """Create MiniMax model via OpenAI-compatible client."""
    client = AsyncOpenAI(
        base_url=MINIMAX_BASE_URL,
        api_key=MINIMAX_API_KEY,
    )
    return OpenAIChatCompletionsModel(
        model=MODEL_NAME,
        openai_client=client,
    )


def create_tools(environment: BaseEnvironment) -> list[FunctionTool]:
    """Create tools for the agent. Add new tools here."""

    @function_tool
    async def run_shell(command: str) -> str:
        """Run a shell command in the task environment. Returns stdout and stderr."""
        try:
            result = await environment.exec(command=command, timeout_sec=120)
            out = ""
            if result.stdout:
                out += result.stdout
            if result.stderr:
                out += f"\nSTDERR:\n{result.stderr}" if out else f"STDERR:\n{result.stderr}"
            return out or "(no output)"
        except Exception as exc:
            return f"ERROR: {exc}"

    @function_tool
    async def write_file(path: str, content: str) -> str:
        """Write content to a file. Creates parent directories if needed."""
        try:
            safe_path = path.replace("'", "'\\''")
            encoded = base64.b64encode(content.encode()).decode()
            result = await environment.exec(
                command=f"mkdir -p $(dirname '{safe_path}') && echo '{encoded}' | base64 -d > '{safe_path}'",
                timeout_sec=30,
            )
            return f"File written: {path}"
        except Exception as exc:
            return f"ERROR writing {path}: {exc}"

    @function_tool
    async def read_file(path: str) -> str:
        """Read the contents of a file."""
        try:
            safe_path = path.replace("'", "'\\''")
            result = await environment.exec(command=f"cat '{safe_path}'", timeout_sec=10)
            return result.stdout or "(empty file)"
        except Exception as exc:
            return f"ERROR reading {path}: {exc}"

    @function_tool
    async def list_files(directory: str = ".") -> str:
        """List files in a directory recursively (excluding node_modules, .next)."""
        try:
            safe_dir = directory.replace("'", "'\\''")
            result = await environment.exec(
                command=f"find '{safe_dir}' -type f -not -path '*/node_modules/*' -not -path '*/.next/*' -not -path '*/.git/*' | head -100",
                timeout_sec=15,
            )
            return result.stdout or "(no files)"
        except Exception as exc:
            return f"ERROR: {exc}"

    return [run_shell, write_file, read_file, list_files]


def create_agent(environment: BaseEnvironment) -> Agent:
    """Build the agent. Modify to add handoffs, sub-agents, or agent-as-tool."""
    tools = create_tools(environment)
    model = _get_model()
    return Agent(
        name="kleap-agent",
        instructions=SYSTEM_PROMPT,
        tools=tools,
        model=model,
    )


async def _pre_read_files(environment: BaseEnvironment) -> str:
    """Pre-read key project files so the agent doesn't need to."""
    files_to_read = [
        "/project/app/page.tsx",
        "/project/app/layout.tsx",
        "/project/app/globals.css",
    ]
    parts = []
    for path in files_to_read:
        try:
            result = await environment.exec(command=f"cat '{path}' 2>/dev/null", timeout_sec=5)
            content = result.stdout
            if content:
                parts.append(f"### {path}\n```tsx\n{content}\n```")
        except Exception:
            pass
    if parts:
        return "\n\n## Current project files\n\n" + "\n\n".join(parts)
    return ""


async def run_task(
    environment: BaseEnvironment,
    instruction: str,
) -> tuple[object, int]:
    """Run the agent on a task and return (result, duration_ms)."""
    agent = create_agent(environment)

    # Pre-read existing files to save the agent from needing read_file calls
    context = await _pre_read_files(environment)

    t0 = time.time()
    enhanced_input = instruction + context
    result = await Runner.run(agent, input=enhanced_input, max_turns=MAX_TURNS)
    duration_ms = int((time.time() - t0) * 1000)
    return result, duration_ms


# ============================================================================
# FIXED ADAPTER BOUNDARY: do not modify unless the human explicitly asks.
# Harbor integration and trajectory serialization live here.
# ============================================================================

def to_atif(result: object, model: str, duration_ms: int = 0) -> dict:
    """Convert OpenAI Agents SDK RunResult to an ATIF trajectory dict."""
    steps: list[dict] = []
    step_id = 0
    now = datetime.now(timezone.utc).isoformat()

    def _step(source: str, message: str, **extra: object) -> dict:
        nonlocal step_id
        step_id += 1
        step = {
            "step_id": step_id,
            "timestamp": now,
            "source": source,
            "message": message,
        }
        step.update({key: value for key, value in extra.items() if value is not None})
        return step

    pending_tool_call = None
    for item in result.new_items:
        if isinstance(item, MessageOutputItem):
            text = ItemHelpers.text_message_output(item)
            if text:
                steps.append(_step("agent", text, model_name=model))
        elif isinstance(item, ReasoningItem):
            summaries = getattr(item.raw_item, "summary", None)
            reasoning = "\n".join(s.text for s in summaries if hasattr(s, "text")) if summaries else None
            if reasoning:
                steps.append(
                    _step(
                        "agent",
                        "(thinking)",
                        reasoning_content=reasoning,
                        model_name=model,
                    )
                )
        elif isinstance(item, ToolCallItem):
            raw = item.raw_item
            if hasattr(raw, "name"):
                pending_tool_call = raw
        elif isinstance(item, ToolCallOutputItem) and pending_tool_call:
            arguments = (
                json.loads(pending_tool_call.arguments)
                if isinstance(pending_tool_call.arguments, str)
                else pending_tool_call.arguments
            )
            output_str = str(item.output) if item.output else ""
            steps.append(
                _step(
                    "agent",
                    f"Tool: {pending_tool_call.name}",
                    tool_calls=[
                        {
                            "tool_call_id": pending_tool_call.call_id,
                            "function_name": pending_tool_call.name,
                            "arguments": arguments,
                        }
                    ],
                    observation={
                        "results": [
                            {
                                "source_call_id": pending_tool_call.call_id,
                                "content": output_str,
                            }
                        ]
                    },
                )
            )
            pending_tool_call = None

    if pending_tool_call:
        arguments = (
            json.loads(pending_tool_call.arguments)
            if isinstance(pending_tool_call.arguments, str)
            else pending_tool_call.arguments
        )
        steps.append(
            _step(
                "agent",
                f"Tool: {pending_tool_call.name}",
                tool_calls=[
                    {
                        "tool_call_id": pending_tool_call.call_id,
                        "function_name": pending_tool_call.name,
                        "arguments": arguments,
                    }
                ],
            )
        )

    if not steps:
        steps.append(_step("user", "(empty)"))

    usage = Usage()
    for response in result.raw_responses:
        usage.add(response.usage)

    return {
        "schema_version": "ATIF-v1.6",
        "session_id": getattr(result, "last_response_id", None) or "unknown",
        "agent": {"name": "kleap-agent", "version": "0.1.0", "model_name": model},
        "steps": steps,
        "final_metrics": {
            "total_prompt_tokens": usage.input_tokens,
            "total_completion_tokens": usage.output_tokens,
            "total_cached_tokens": getattr(usage.input_tokens_details, "cached_tokens", 0) or 0,
            "total_cost_usd": None,
            "total_steps": len(steps),
            "extra": {"duration_ms": duration_ms, "num_turns": len(result.raw_responses)},
        },
    }


class AutoAgent(BaseAgent):
    """Harbor agent adapter. Runs the MiniMax agent host-side and proxies shell into the container."""

    SUPPORTS_ATIF = True

    def __init__(self, *args, extra_env: dict[str, str] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._extra_env = dict(extra_env) if extra_env else {}

    @staticmethod
    def name() -> str:
        return "kleap-agent"

    def version(self) -> str | None:
        return "0.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        pass

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        await environment.exec(command="mkdir -p /task")
        instr_file = self.logs_dir / "instruction.md"
        instr_file.write_text(instruction)
        await environment.upload_file(source_path=instr_file, target_path="/task/instruction.md")

        result, duration_ms = await run_task(environment, instruction)

        atif = to_atif(result, model=MODEL_NAME, duration_ms=duration_ms)
        traj_path = self.logs_dir / "trajectory.json"
        traj_path.write_text(json.dumps(atif, indent=2))

        try:
            final_metrics = atif.get("final_metrics", {})
            context.n_input_tokens = final_metrics.get("total_prompt_tokens", 0)
            context.n_output_tokens = final_metrics.get("total_completion_tokens", 0)
            context.n_cache_tokens = final_metrics.get("total_cached_tokens", 0)
        except Exception:
            pass

        usage = Usage()
        for response in result.raw_responses:
            usage.add(response.usage)
        print(
            f"turns={len(result.raw_responses)} duration_ms={duration_ms} "
            f"input={usage.input_tokens} output={usage.output_tokens}"
        )


__all__ = ["AutoAgent"]
