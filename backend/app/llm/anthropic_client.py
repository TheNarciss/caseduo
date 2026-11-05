"""Lazy singleton around `anthropic.AsyncAnthropic`, and the per-model request knobs.

Same design as Tangent's `app/llm/anthropic_client.py`: lazy init (the app
boots without a key, LLM routes answer 503), one place for the model and
its parameters.

One model for generation and grading, as asked: `CASEDUO_MODEL`, default
`claude-sonnet-4-5`. That model retires on 2026-11-30 (DEVIATIONS D1): the
helpers below adapt the request to whichever model is configured, so
switching to `claude-sonnet-5-5` is a one-line change in `.env`.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

MODEL: str = os.getenv("CASEDUO_MODEL", "claude-sonnet-4-5").strip() or "claude-sonnet-4-5"

GENERATION_MAX_TOKENS = 16_000
GRADING_MAX_TOKENS = 6_000
GENERATION_EFFORT = "high"  # the model answers are the product
GRADING_EFFORT = "medium"  # the user is waiting

WEB_SEARCH_MAX_USES = int(os.getenv("GENERATION_WEB_SEARCH_MAX_USES", "3"))

# Models that take the dynamic-filtering web search (`web_search_20260209`)
# and adaptive thinking with an effort level. Older ones (Sonnet 4.5, Haiku
# 4.5) take the basic tool and no effort.
_CURRENT_PREFIXES = (
    "claude-sonnet-5",
    "claude-sonnet-4-6",
    "claude-opus-5",
    "claude-opus-4-6",
    "claude-opus-4-7",
    "claude-opus-4-8",
    "claude-fable",
)


def is_current_generation(model: str) -> bool:
    return model.startswith(_CURRENT_PREFIXES)


def web_search_tool(model: str = MODEL, max_uses: int = WEB_SEARCH_MAX_USES) -> dict[str, Any]:
    """Anthropic's server-side web search, in the variant the model takes."""
    tool_type = "web_search_20260209" if is_current_generation(model) else "web_search_20250305"
    return {"type": tool_type, "name": "web_search", "max_uses": max_uses}


def reasoning_params(model: str = MODEL, *, effort: str) -> dict[str, Any]:
    """Adaptive thinking + effort on current models; nothing on Sonnet 4.5 (it rejects effort)."""
    if not is_current_generation(model):
        return {}
    return {"thinking": {"type": "adaptive"}, "output_config": {"effort": effort}}


def cached_system(text: str) -> list[dict[str, Any]]:
    """The system prompt as one cached block: it never changes between calls."""
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    """Process-wide `AsyncAnthropic`. Raises RuntimeError without ANTHROPIC_API_KEY."""
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY manquante : mets-la dans backend/.env pour activer "
                "la génération et la notation."
            )
        logger.info("Initializing AsyncAnthropic client (model=%s)", MODEL)
        _client = AsyncAnthropic(api_key=api_key, max_retries=2)
    return _client


def set_client_for_testing(client: Any | None) -> None:
    """Tests only: inject a fake client (or reset with None)."""
    global _client
    _client = client
