"""Message Batches (−50 %): submit tomorrow's exercises at 03:00, poll every 30 min,
insert as soon as results land, redo failures synchronously.

Same pipeline as Tangent's batch_submitter / batch_poller: one `cron_runs`
row per batch (`job = batch`), `custom_id` routes each result back to its
slot, UNIQUE(date, slot) makes every insert idempotent — the 05:30 sync
fallback and a late batch can never duplicate an exercise.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import CronRun
from ..llm import anthropic_client, cost_tracker
from ..llm._retry import retry_on_overload
from ..llm.cost_tracker import Usage, usage_of
from . import request, service
from .planner import SlotSpec
from .sync import parse_message

logger = logging.getLogger(__name__)

# Conservative per-slot estimate for the kill-switch (real cost comes from usage).
_EST_INPUT, _EST_OUTPUT, _EST_SEARCHES = 20_000, 4_000, 2


def custom_id(day: date, slot: str) -> str:
    """`gen_20261106_case_cadrage` (custom ids allow letters, digits, `_` and `-` only)."""
    return f"gen_{day:%Y%m%d}_{slot}"


def parse_custom_id(value: str) -> tuple[date, str] | None:
    parts = value.split("_", 2)
    if len(parts) != 3 or parts[0] != "gen":
        return None
    try:
        return datetime.strptime(parts[1], "%Y%m%d").date(), parts[2]
    except ValueError:
        return None


def estimate_cost(specs: list[SlotSpec]) -> float:
    total = 0.0
    for spec in specs:
        total += cost_tracker.compute_cost_usd(
            anthropic_client.MODEL,
            input_tokens=_EST_INPUT,
            output_tokens=_EST_OUTPUT,
            web_searches=_EST_SEARCHES if spec.web_search else 0,
            batch=True,
        )
    return total


async def in_progress_runs(session: AsyncSession, day: date | None = None) -> list[CronRun]:
    stmt = select(CronRun).where(CronRun.job == "batch", CronRun.status == "in_progress")
    if day is not None:
        stmt = stmt.where(CronRun.target_date == day)
    return list((await session.execute(stmt.order_by(CronRun.started_at))).scalars().all())


@retry_on_overload
async def _create_batch(client: Any, requests: list[Request]) -> Any:
    return await client.messages.batches.create(requests=requests)


async def submit_batch(session: AsyncSession, day: date) -> CronRun | None:
    """Submit every missing slot of `day`. None when there is nothing to do."""
    plan, ctx = await service.plan_for(session, day)
    todo = await service.missing_slots(session, plan)
    if not todo:
        logger.info("Batch %s: day already complete", day)
        return None
    if await in_progress_runs(session, day):
        logger.info("Batch %s: a batch is already in flight", day)
        return None
    estimate = estimate_cost(todo)
    budget = await cost_tracker.budget_left_usd(session)
    if budget < estimate:
        logger.warning("Batch %s refused: estimate $%.3f > budget $%.3f", day, estimate, budget)
        return None

    requests = [
        Request(
            custom_id=custom_id(day, spec.slot),
            params=MessageCreateParamsNonStreaming(**request.params(plan, spec, ctx)),  # type: ignore[typeddict-item]
        )
        for spec in todo
    ]
    client = anthropic_client.get_client()
    anthropic_batch = await _create_batch(client, requests)
    run = CronRun(
        job="batch",
        target_date=day,
        anthropic_batch_id=anthropic_batch.id,
        status="in_progress",
        model=anthropic_client.MODEL,
        n_requests=len(requests),
        estimated_cost_usd=round(estimate, 4),
        errors=[],
    )
    session.add(run)
    await session.commit()
    logger.info("Batch submitted for %s: %s (%d requests)", day, anthropic_batch.id, len(requests))
    return run


async def _process(session: AsyncSession, run: CronRun) -> bool:
    """Read one batch. False while Anthropic is still processing it."""
    client = anthropic_client.get_client()
    batch_id = run.anthropic_batch_id or ""
    batch = await client.messages.batches.retrieve(batch_id)
    if getattr(batch, "processing_status", None) != "ended":
        return False

    day = run.target_date
    plan, ctx = await service.plan_for(session, day)
    by_slot = {s.slot: s for s in plan.slots}
    usage = Usage()
    failed: list[str] = []
    errors: list[dict[str, Any]] = list(run.errors or [])

    async for result in await client.messages.batches.results(batch_id):
        parsed = parse_custom_id(result.custom_id)
        spec = by_slot.get(parsed[1]) if parsed else None
        if spec is None:
            errors.append({"custom_id": result.custom_id, "error": "custom_id inconnu"})
            continue
        kind = getattr(result.result, "type", None)
        if kind != "succeeded":
            failed.append(spec.slot)
            errors.append({"slot": spec.slot, "attempt": "batch", "error": f"batch: {kind}"})
            continue
        message = result.result.message  # type: ignore[union-attr]
        usage.add(usage_of(message, batch=True))
        try:
            fields = parse_message(message, spec, ctx)
        except ValueError as exc:
            failed.append(spec.slot)
            errors.append({"slot": spec.slot, "attempt": "batch", "error": str(exc)[:500]})
            continue
        inserted = await service.insert_exercise(
            session,
            day,
            spec.slot,
            fields,
            mode="batch",
            run_id=run.id,
            model=getattr(message, "model", None) or anthropic_client.MODEL,
        )
        run.n_succeeded += int(inserted)
        await session.commit()

    cost_tracker.apply_to_run(run, usage)
    run.n_failed = len(failed)
    run.errors = errors
    run.status = "ended" if not failed else ("partial" if run.n_succeeded else "failed")
    run.finished_at = datetime.now(UTC)
    await cost_tracker.record_cost(session, usage.cost_usd, commit=False)
    await session.commit()
    logger.info(
        "Batch %s for %s ended: %d ok, %d failed, $%.4f",
        run.anthropic_batch_id,
        day,
        run.n_succeeded,
        len(failed),
        usage.cost_usd,
    )
    if failed:  # the batch was the first try; two more, synchronously
        try:
            await service.generate_day_sync(session, day, job="sync", only=failed)
        except Exception:
            logger.exception("Sync redo of failed batch slots for %s failed", day)
            await session.rollback()
    return True


async def poll_batches(session: AsyncSession) -> int:
    """Poll every in-flight batch. Returns how many were finalized."""
    finalized = 0
    for run in await in_progress_runs(session):
        run_id = run.id
        try:
            finalized += int(await _process(session, run))
        except Exception:
            logger.exception("Polling batch run %s failed, will retry", run_id)
            await session.rollback()
    return finalized


async def cancel_in_flight(session: AsyncSession, day: date) -> int:
    """Ask Anthropic to cancel the batches still running for `day` (best effort).

    They stay `in_progress` here: the poller reads what they produced once
    the cancellation ends; nothing is inserted twice.
    """
    n = 0
    for run in await in_progress_runs(session, day):
        try:
            await anthropic_client.get_client().messages.batches.cancel(
                run.anthropic_batch_id or ""
            )
            n += 1
        except Exception:
            logger.exception("Cancel of batch %s failed", run.anthropic_batch_id)
    return n
