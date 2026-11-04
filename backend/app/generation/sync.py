"""Synchronous generation of one slot: call Claude, parse, validate, retry twice.

Used by the seed script, the 05:30 fallback, and to redo slots a batch
failed. Each attempt's tokens and cost are counted, failed or not.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from anthropic import APIConnectionError, APIStatusError

from ..llm import anthropic_client
from ..llm.cost_tracker import Usage, usage_of
from ..llm.messages import extract_json, final_text, search_urls
from . import request, schema
from .context import GenerationContext
from .planner import DayPlan, SlotSpec

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3  # 1 + 2 retries, as asked
MAX_PAUSE_CONTINUATIONS = 3


@dataclass
class SlotResult:
    spec: SlotSpec
    fields: dict[str, Any] | None = None
    usage: Usage = field(default_factory=Usage)
    errors: list[dict[str, Any]] = field(default_factory=list)


async def _create(client: Any, params: dict[str, Any]) -> Any:
    """messages.create, continuing a server-tool turn the API paused (`pause_turn`)."""
    message = await client.messages.create(**params)
    messages = list(params["messages"])
    for _ in range(MAX_PAUSE_CONTINUATIONS):
        if getattr(message, "stop_reason", None) != "pause_turn":
            break
        messages = [*messages, {"role": "assistant", "content": message.content}]
        message = await client.messages.create(**{**params, "messages": messages})
    return message


def parse_message(
    message: Any,
    spec: SlotSpec,
    ctx: GenerationContext,
) -> dict[str, Any]:
    """Validated exercise fields from one model answer, or GenerationInvalid/ValueError."""
    stop = getattr(message, "stop_reason", None)
    if stop in ("refusal", "max_tokens", "pause_turn"):
        raise schema.GenerationInvalid(f"stop_reason={stop}")
    data = extract_json(final_text(message))
    return schema.validate(
        data,
        spec,
        search_urls=search_urls(message) if spec.web_search else None,
        weaknesses=ctx.weakness_keys,
        recent_titles=ctx.recent_titles.get(spec.type),
    )


async def generate_slot(plan: DayPlan, spec: SlotSpec, ctx: GenerationContext) -> SlotResult:
    """Up to three attempts for one slot. Raises RuntimeError if no API key."""
    client = anthropic_client.get_client()
    result = SlotResult(spec=spec)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            message = await _create(client, request.params(plan, spec, ctx))
        except (APIStatusError, APIConnectionError) as exc:
            result.errors.append(
                {"slot": spec.slot, "attempt": attempt, "error": f"API: {exc.__class__.__name__}"}
            )
            logger.warning("Generation %s attempt %d: API error %s", spec.slot, attempt, exc)
            continue
        result.usage.add(usage_of(message))
        try:
            result.fields = parse_message(message, spec, ctx)
            return result
        except ValueError as exc:
            result.errors.append({"slot": spec.slot, "attempt": attempt, "error": str(exc)[:500]})
            logger.warning("Generation %s attempt %d rejected: %s", spec.slot, attempt, exc)
    return result
