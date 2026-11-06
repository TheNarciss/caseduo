"""Synchronous generation of one slot: call Claude, parse, validate, retry twice.

Used every night with Claude Code (DEVIATIONS D15), by the seed script, the 05:30
fallback, and to redo slots a batch failed. Each attempt's tokens and cost are
counted, failed or not.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from anthropic import APIConnectionError, APIStatusError

from ..llm import anthropic_client, claude_code, prompts
from ..llm.cost_tracker import Usage, usage_of
from ..llm.messages import extract_json, final_text, normalize_url, search_urls
from . import provider, request, schema
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


async def _generate_slot_cli(plan: DayPlan, spec: SlotSpec, ctx: GenerationContext) -> SlotResult:
    """The same three attempts, written by Claude Code; its web search replaces the API's."""
    result = SlotResult(spec=spec)
    tools = ["WebSearch"] if spec.web_search and anthropic_client.WEB_SEARCH_MAX_USES > 0 else []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        run = claude_code.Run()
        try:
            await claude_code.ask(
                prompts.load("generate"),
                request.user_message(plan, spec, ctx),
                run,
                tools=tools,
                pool="generation",
                timeout=claude_code.GENERATION_TIMEOUT_SECONDS,
                model_name=claude_code.generation_model(),
                effort_level=claude_code.generation_effort(),
            )
        except claude_code.ClaudeCodeError as exc:
            result.errors.append({"slot": spec.slot, "attempt": attempt, "error": str(exc)})
            logger.warning("Generation %s attempt %d: %s", spec.slot, attempt, exc)
            continue
        run.usage.models = {run.model} if run.model else run.usage.models
        result.usage.add(run.usage)
        try:
            result.fields = schema.validate(
                extract_json(run.final_text or run.text),
                spec,
                search_urls={normalize_url(u) for u in run.urls} if spec.web_search else None,
                weaknesses=ctx.weakness_keys,
                recent_titles=ctx.recent_titles.get(spec.type),
            )
            return result
        except ValueError as exc:
            result.errors.append({"slot": spec.slot, "attempt": attempt, "error": str(exc)[:500]})
            logger.warning("Generation %s attempt %d rejected: %s", spec.slot, attempt, exc)
    return result


async def generate_slot(plan: DayPlan, spec: SlotSpec, ctx: GenerationContext) -> SlotResult:
    """Up to three attempts for one slot, by Claude Code when its token is set, else by the
    API. Raises RuntimeError if neither is configured."""
    if provider.provider() == "claude_code":
        return await _generate_slot_cli(plan, spec, ctx)
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
