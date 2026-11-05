"""Claude Code as the grader, on the owner's Claude subscription (DEVIATIONS D14).

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
import shutil
import tempfile
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from .cost_tracker import Usage

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 180
_slots: asyncio.Semaphore | None = None


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


def token() -> str:
    return os.getenv("CLAUDE_CODE_OAUTH_TOKEN", "").strip()


def available() -> bool:
    return bool(token()) and shutil.which(binary()) is not None


def _semaphore() -> asyncio.Semaphore:
    """Several answers at once are graded side by side, a few CLI processes at a time."""
    global _slots
    if _slots is None:
        _slots = asyncio.Semaphore(int(os.getenv("CLAUDE_CODE_MAX_PARALLEL", "3")))
    return _slots


def command(system_prompt: str) -> list[str]:
    return [
        binary(),
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-partial-messages",
        "--tools",
        "",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--disable-slash-commands",
        "--model",
        model(),
        "--effort",
        effort(),
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
    """Filled while `stream` runs: the model that answered, the usage, the whole text."""

    model: str = ""
    usage: Usage = field(default_factory=Usage)
    text: str = ""


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
            "La limite d'usage de l'abonnement Claude est atteinte : la notation reprend à sa "
            "remise à zéro. Ta réponse n'est pas perdue, renvoie-la plus tard."
        )
    if any(
        word in lowered for word in ("401", "authentication", "oauth", "login", "invalid api key")
    ):
        return "Le jeton Claude Code du serveur est refusé : il faut en refaire un (claude setup-token)."
    return "Claude est surchargé, réessaie dans une minute."


async def stream(system_prompt: str, user_message: str, run: Run) -> AsyncIterator[str]:
    """Yields the answer's text as it is written. Raises ClaudeCodeError on failure."""
    if not available():
        raise ClaudeCodeError("La notation n'est pas configurée sur le serveur.")
    async with _semaphore():
        workdir = Path(tempfile.mkdtemp(prefix="caseduo-grade-"))
        home = Path(tempfile.gettempdir()) / "caseduo-claude-home"
        home.mkdir(exist_ok=True)
        stderr_path = workdir / "stderr.log"
        result: dict | None = None
        streamed = False
        with stderr_path.open("wb") as stderr:
            proc = await asyncio.create_subprocess_exec(
                *command(system_prompt),
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
                async with asyncio.timeout(TIMEOUT_SECONDS):
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
    if not run.text and result.get("result"):
        run.text = str(result["result"])
        yield run.text
    run.usage = usage_of(result)
    run.model = run.model or next(iter(run.usage.models), "") or model()
