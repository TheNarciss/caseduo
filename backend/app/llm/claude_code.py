"""Claude Code on the owner's Claude subscription: the grader (DEVIATIONS D14) and the
writer of the daily exercises (D15).

`claude -p` runs headless inside the backend container, authenticated by
CLAUDE_CODE_OAUTH_TOKEN (made once with `claude setup-token`). No tools, no MCP,
no slash commands, no session saved: one system prompt (prompts/grade.md), one
user message, and the text streamed back as the model writes it. The output is
the same tagged text as through the API, so the parser, the server-side score
and the SSE route do not change.

Settings are read at each call, so a new token in backend/.env applies after a
`docker compose up -d backend`, and tests can switch them with environment
variables.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .cost_tracker import Usage

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 180
GENERATION_TIMEOUT_SECONDS = 900  # web searches, then a long JSON
_pools: dict[str, asyncio.Semaphore] = {}
_URL = re.compile(r"https?://[^\s\"'<>\\)\]]+")


class ClaudeCodeError(RuntimeError):
    """The CLI failed. The message is in French, ready for the user."""


def binary() -> str:
    return os.getenv("CLAUDE_CODE_BIN", "claude").strip() or "claude"


def model() -> str:
    """An alias (`sonnet`, `opus`) follows the current model: no retirement date to track."""
    return os.getenv("CLAUDE_CODE_MODEL", "sonnet").strip() or "sonnet"


def effort() -> str:
    """`low` by default: the user is waiting for the score, about 20 seconds."""
    return os.getenv("CLAUDE_CODE_EFFORT", "low").strip() or "low"


def generation_model() -> str:
    return os.getenv("CLAUDE_CODE_GENERATION_MODEL", "").strip() or model()


def generation_effort() -> str:
    """`high` by default: nobody waits at night, and the model answers are the product."""
    return os.getenv("CLAUDE_CODE_GENERATION_EFFORT", "high").strip() or "high"


def token() -> str:
    return os.getenv("CLAUDE_CODE_OAUTH_TOKEN", "").strip()


def available() -> bool:
    return bool(token()) and shutil.which(binary()) is not None


def _semaphore(pool: str) -> asyncio.Semaphore:
    """Gradings and generations have their own slots: a night of generation never makes
    a user wait for a score. Within a pool, a few CLI processes run side by side."""
    if pool not in _pools:
        name = (
            "CLAUDE_CODE_MAX_PARALLEL" if pool == "grading" else "CLAUDE_CODE_GENERATION_PARALLEL"
        )
        _pools[pool] = asyncio.Semaphore(int(os.getenv(name, "3" if pool == "grading" else "2")))
    return _pools[pool]


def command(
    system_prompt: str,
    *,
    tools: Sequence[str] = (),
    model_name: str | None = None,
    effort_level: str | None = None,
) -> list[str]:
    """No tools unless asked (web search for the cases), then allowed without a prompt."""
    allowed = ",".join(tools)
    out = [
        binary(),
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-partial-messages",
        "--tools",
        allowed,
    ]
    if allowed:
        out += ["--allowedTools", allowed]
    return [
        *out,
        "--strict-mcp-config",
        "--no-session-persistence",
        "--disable-slash-commands",
        "--model",
        model_name or model(),
        "--effort",
        effort_level or effort(),
        "--system-prompt",
        system_prompt,
    ]


def environment(home: str) -> dict[str, str]:
    """Only what the CLI needs. ANTHROPIC_API_KEY stays out: with it, the CLI would bill the API."""
    return {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": home,
        "LANG": "C.UTF-8",
        "CLAUDE_CODE_OAUTH_TOKEN": token(),
        "DISABLE_AUTOUPDATER": "1",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    }


@dataclass
class Run:
    """Filled while `stream` runs: the model that answered, the usage, the whole text, the
    text of the last turn (after the searches) and every URL the web search returned."""

    model: str = ""
    usage: Usage = field(default_factory=Usage)
    text: str = ""
    final_text: str = ""
    urls: set[str] = field(default_factory=set)


def tool_result_urls(event: dict) -> set[str]:
    """URLs in a tool result: the structured search results, else any URL in the text."""
    urls: set[str] = set()
    structured = event.get("tool_use_result")
    if isinstance(structured, dict):
        for group in structured.get("results") or []:
            if isinstance(group, dict):
                for item in group.get("content") or []:
                    if isinstance(item, dict) and isinstance(item.get("url"), str):
                        urls.add(item["url"])
    for block in (event.get("message") or {}).get("content") or []:
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        content = block.get("content")
        texts = (
            [content]
            if isinstance(content, str)
            else [c.get("text", "") for c in content or [] if isinstance(c, dict)]
        )
        for text in texts:
            urls.update(_URL.findall(text or ""))
    return urls


def usage_of(result: dict) -> Usage:
    """Token counts from the CLI's final event. Cost 0: the subscription pays, not the API."""
    u = result.get("usage") or {}

    def n(name: str) -> int:
        try:
            return int(u.get(name) or 0)
        except (TypeError, ValueError):
            return 0

    return Usage(
        input_tokens=n("input_tokens"),
        output_tokens=n("output_tokens"),
        cache_read_tokens=n("cache_read_input_tokens"),
        cache_write_tokens=n("cache_creation_input_tokens"),
        cost_usd=0.0,
        calls=1,
        models=set((result.get("modelUsage") or {}).keys()),
    )


def user_message_for(detail: str) -> str:
    """The CLI's error, said to the user."""
    lowered = detail.lower()
    if "limit" in lowered and ("usage" in lowered or "hit" in lowered or "reached" in lowered):
        return (
            "La limite d'usage de l'abonnement Claude est atteinte : ça reprend à sa remise à "
            "zéro. Ta réponse n'est pas perdue, renvoie-la plus tard."
        )
    if any(
        word in lowered for word in ("401", "authentication", "oauth", "login", "invalid api key")
    ):
        return "Le jeton Claude Code du serveur est refusé : il faut en refaire un (claude setup-token)."
    return "Claude est surchargé, réessaie dans une minute."


async def stream(
    system_prompt: str,
    user_message: str,
    run: Run,
    *,
    tools: Sequence[str] = (),
    pool: str = "grading",
    timeout: float = TIMEOUT_SECONDS,
    model_name: str | None = None,
    effort_level: str | None = None,
) -> AsyncIterator[str]:
    """Yields the answer's text as it is written. Raises ClaudeCodeError on failure."""
    if not available():
        raise ClaudeCodeError("La notation n'est pas configurée sur le serveur.")
    async with _semaphore(pool):
        workdir = Path(tempfile.mkdtemp(prefix="caseduo-grade-"))
        home = Path(tempfile.gettempdir()) / "caseduo-claude-home"
        home.mkdir(exist_ok=True)
        stderr_path = workdir / "stderr.log"
        result: dict | None = None
        streamed = False
        with stderr_path.open("wb") as stderr:
            proc = await asyncio.create_subprocess_exec(
                *command(
                    system_prompt, tools=tools, model_name=model_name, effort_level=effort_level
                ),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=stderr,
                cwd=workdir,
                env=environment(str(home)),
                limit=8 * 1024 * 1024,
            )
            try:
                assert proc.stdin is not None and proc.stdout is not None
                proc.stdin.write(user_message.encode("utf-8"))
                await proc.stdin.drain()
                proc.stdin.close()
                async with asyncio.timeout(timeout):
                    async for raw in proc.stdout:
                        try:
                            event = json.loads(raw)
                        except ValueError:
                            continue
                        kind = event.get("type")
                        if kind == "system" and event.get("subtype") == "init":
                            run.model = event.get("model") or run.model
                        elif kind == "stream_event":
                            ev = event.get("event") or {}
                            delta = ev.get("delta") or {}
                            if (
                                ev.get("type") == "content_block_delta"
                                and delta.get("type") == "text_delta"
                            ):
                                text = delta.get("text") or ""
                                if text:
                                    streamed = True
                                    run.text += text
                                    yield text
                        elif kind == "assistant" and not streamed:
                            # Without partial messages, the whole text comes in one message.
                            for block in (event.get("message") or {}).get("content") or []:
                                if block.get("type") == "text" and block.get("text"):
                                    run.text += block["text"]
                                    yield block["text"]
                        elif kind == "user":
                            run.urls |= tool_result_urls(event)
                        elif kind == "result":
                            result = event
                    await proc.wait()
            except TimeoutError as exc:
                raise ClaudeCodeError(
                    "Claude met trop de temps à répondre, réessaie dans une minute."
                ) from exc
            finally:
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()
        stderr_tail = stderr_path.read_text(errors="replace")[-1000:]
        shutil.rmtree(workdir, ignore_errors=True)

    if result is None or result.get("is_error"):
        detail = str((result or {}).get("result") or stderr_tail or f"exit {proc.returncode}")
        logger.warning("Claude Code grading failed: %s", detail[:500])
        raise ClaudeCodeError(user_message_for(detail))
    run.final_text = str(result.get("result") or "")
    if not run.text and run.final_text:
        run.text = run.final_text
        yield run.text
    run.usage = usage_of(result)
    run.model = run.model or next(iter(run.usage.models), "") or model()


async def ask(system_prompt: str, user_message: str, run: Run, **options) -> Run:
    """The whole answer at once (generation): same options as `stream`."""
    async for _ in stream(system_prompt, user_message, run, **options):
        pass
    return run
