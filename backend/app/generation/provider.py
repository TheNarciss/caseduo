"""Who writes the exercises (DEVIATIONS D15): Claude Code on the subscription, or the API.

GENERATION_PROVIDER=auto (the default) and claude_code take Claude Code as soon as its
token is set; auto falls back to the API when its key is set; api forces the API.
"""

from __future__ import annotations

import os

from ..llm import anthropic_client, claude_code


def provider() -> str | None:
    choice = os.getenv("GENERATION_PROVIDER", "auto").strip().lower() or "auto"
    if choice in ("auto", "claude_code") and claude_code.available():
        return "claude_code"
    if choice in ("auto", "api"):
        try:
            anthropic_client.get_client()
        except RuntimeError:
            return None
        return "api"
    return None


def model_name(chosen: str | None) -> str:
    return claude_code.generation_model() if chosen == "claude_code" else anthropic_client.MODEL
