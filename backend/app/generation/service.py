"""Generation orchestration: which slots are missing, sync generation of a day,
the never-an-empty-day guarantee, insertion (idempotent on UNIQUE(date, slot))."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..content import starter_pack
from ..db.models import CronRun, Exercise
from ..errors import LLMUnavailableError
from ..llm import anthropic_client, cost_tracker
from .context import GenerationContext, build_context
from .planner import DayPlan, SlotSpec, plan_day
from .sync import generate_slot

logger = logging.getLogger(__name__)

SYNC_CONCURRENCY = 3


async def plan_for(session: AsyncSession, day: date) -> tuple[DayPlan, GenerationContext]:
    ctx = await build_context(session, day)
    plan = plan_day(day, easy_mode=ctx.easy_mode, has_weaknesses=bool(ctx.weaknesses))
    return plan, ctx


async def existing_slots(session: AsyncSession, day: date) -> set[str]:
    rows = await session.execute(select(Exercise.slot).where(Exercise.date == day))
    return set(rows.scalars().all())


async def count_exercises(session: AsyncSession, day: date) -> int:
    stmt = select(func.count()).select_from(Exercise).where(Exercise.date == day)
    return int((await session.execute(stmt)).scalar() or 0)


async def missing_slots(session: AsyncSession, plan: DayPlan) -> list[SlotSpec]:
    have = await existing_slots(session, plan.day)
    return [s for s in plan.slots if s.slot not in have]


async def insert_exercise(
    session: AsyncSession,
    day: date,
    slot: str,
    fields: dict[str, Any],
    *,
    mode: str,
    run_id: uuid.UUID | None,
    model: str | None,
) -> bool:
    """Insert unless the slot already exists. True if inserted. Not committed."""
    stmt = (
        pg_insert(Exercise)
        .values(
            id=uuid.uuid4(),
            date=day,
            slot=slot,
            generation_mode=mode,
            cron_run_id=run_id,
            model_used=model,
            **fields,
        )
        .on_conflict_do_nothing(constraint="uq_exercises_date_slot")
    )
    result = await session.execute(stmt)
    return bool(result.rowcount)  # type: ignore[attr-defined]


async def generate_day_sync(
    session: AsyncSession,
    day: date,
    *,
    job: str = "sync",
    only: list[str] | None = None,
) -> CronRun | None:
    """Generate every missing slot of `day` synchronously. Idempotent.

    Returns the cron_runs row (None when nothing was missing). Raises
    LLMUnavailableError when no API key is configured.
    """
    plan, ctx = await plan_for(session, day)
    todo = await missing_slots(session, plan)
    if only is not None:
        todo = [s for s in todo if s.slot in only]
    if not todo:
        logger.info("Generation %s: nothing missing for %s", job, day)
        return None
    try:
        anthropic_client.get_client()
    except RuntimeError as exc:
        raise LLMUnavailableError(str(exc)) from exc

    run = CronRun(
        job=job,
        target_date=day,
        status="running",
        model=anthropic_client.MODEL,
        n_requests=len(todo),
        errors=[],
    )
    session.add(run)
    await session.commit()

    budget = await cost_tracker.budget_left_usd(session)
    spent = 0.0
    sem = asyncio.Semaphore(SYNC_CONCURRENCY)
    stop = asyncio.Event()

    async def one(spec: SlotSpec):
        async with sem:
            if stop.is_set():
                return None
            return await generate_slot(plan, spec, ctx)

    errors: list[dict[str, Any]] = []
    for next_done in asyncio.as_completed([one(s) for s in todo]):
        result = await next_done
        if result is None:
            continue
        cost_tracker.apply_to_run(run, result.usage)
        spent += result.usage.cost_usd
        await cost_tracker.record_cost(session, result.usage.cost_usd, commit=False)
        errors += result.errors
        if result.fields is not None:
            inserted = await insert_exercise(
                session,
                day,
                result.spec.slot,
                result.fields,
                mode=job,
                run_id=run.id,
                model=next(iter(result.usage.models), anthropic_client.MODEL),
            )
            run.n_succeeded += int(inserted)
        else:
            run.n_failed += 1
        if spent >= budget:
            stop.set()
            errors.append({"error": f"plafond journalier atteint (${budget:.2f})"})
        run.errors = list(errors)
        await session.commit()

    skipped = run.n_requests - run.n_succeeded - run.n_failed
    run.n_failed += max(0, skipped)
    run.status = "ended" if run.n_failed == 0 else ("partial" if run.n_succeeded else "failed")
    run.finished_at = datetime.now(UTC)
    await session.commit()
    logger.info(
        "Generation %s for %s: %d/%d ok, $%.4f",
        job,
        day,
        run.n_succeeded,
        run.n_requests,
        run.cost_usd,
    )
    return run


async def insert_starter_pack(session: AsyncSession, day: date) -> int:
    """Hand-written exercises for a day that has nothing (DEVIATIONS D11)."""
    inserted = 0
    for slot, fields in starter_pack.exercises():
        inserted += int(
            await insert_exercise(
                session, day, slot, fields, mode="starter", run_id=None, model=None
            )
        )
    await session.commit()
    if inserted:
        logger.warning("Starter pack inserted for %s (%d exercises)", day, inserted)
    return inserted


async def ensure_day(session: AsyncSession, day: date, *, job: str = "fallback") -> None:
    """Never an empty day: generate what is missing; if that is impossible and the
    day is still empty, insert the hand-written starter pack."""
    try:
        await generate_day_sync(session, day, job=job)
    except LLMUnavailableError as exc:
        logger.warning("ensure_day %s: %s", day, exc)
    except Exception:
        logger.exception("ensure_day %s: generation crashed", day)
        await session.rollback()
    if await count_exercises(session, day) == 0:
        await insert_starter_pack(session, day)
