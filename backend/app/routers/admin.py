"""Admin (superuser) routes: review a day, flag a bad correction, regenerate, cron runs."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_superuser
from ..catalog import TYPE_LABELS
from ..db import get_session
from ..db.models import Attempt, CronRun, Exercise
from ..errors import NotFoundError
from ..generation import batch, service

router = APIRouter(prefix="/admin", tags=["admin"])


def cron_dict(r: CronRun) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "job": r.job,
        "target_date": r.target_date.isoformat(),
        "anthropic_batch_id": r.anthropic_batch_id,
        "status": r.status,
        "model": r.model,
        "n_requests": r.n_requests,
        "n_succeeded": r.n_succeeded,
        "n_failed": r.n_failed,
        "input_tokens": r.input_tokens,
        "output_tokens": r.output_tokens,
        "cache_read_tokens": r.cache_read_tokens,
        "cache_write_tokens": r.cache_write_tokens,
        "web_searches": r.web_searches,
        "estimated_cost_usd": r.estimated_cost_usd,
        "cost_usd": r.cost_usd,
        "errors": r.errors,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    }


def review_dict(ex: Exercise) -> dict[str, Any]:
    return {
        "id": str(ex.id),
        "slot": ex.slot,
        "type": ex.type,
        "type_label": TYPE_LABELS.get(ex.type, ex.type),
        "style": ex.style,
        "language": ex.language,
        "difficulty": ex.difficulty,
        "sector": ex.sector,
        "title": ex.title,
        "prompt": ex.prompt,
        "parts": ex.parts,
        "context_data": ex.context_data,
        "model_answer": ex.model_answer,
        "rubric": ex.rubric,
        "sources": ex.sources,
        "targets_weakness": ex.targets_weakness,
        "estimated_minutes": ex.estimated_minutes,
        "flagged": ex.flagged,
        "flag_note": ex.flag_note,
        "generation_mode": ex.generation_mode,
        "model_used": ex.model_used,
    }


async def review_data(session: AsyncSession, day: date) -> dict[str, Any]:
    exercises = (
        await session.execute(select(Exercise).where(Exercise.date == day).order_by(Exercise.slot))
    ).scalars()
    runs = (
        await session.execute(
            select(CronRun).where(CronRun.target_date == day).order_by(CronRun.started_at)
        )
    ).scalars()
    run_list = [cron_dict(r) for r in runs]
    return {
        "date": day.isoformat(),
        "exercises": [review_dict(e) for e in exercises],
        "cron_runs": run_list,
        "cost_usd": round(sum(r["cost_usd"] for r in run_list), 4),
    }


@router.get("/review/{day}")
async def review(
    day: date,
    _: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_session),
):
    return await review_data(session, day)


class FlagIn(BaseModel):
    flagged: bool = True
    note: str | None = Field(default=None, max_length=2000)


@router.post("/exercises/{exercise_id}/flag")
async def flag(
    exercise_id: uuid.UUID,
    body: FlagIn,
    _: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_session),
):
    """A bad correction: out of the revenges, kept as material for prompt tuning."""
    ex = await session.get(Exercise, exercise_id)
    if ex is None:
        raise NotFoundError("Exercice introuvable.")
    ex.flagged = body.flagged
    ex.flag_note = body.note if body.flagged else None
    await session.commit()
    return review_dict(ex)


class GenerateIn(BaseModel):
    date: date
    mode: Literal["sync", "batch"] = "sync"
    force: bool = False


@router.post("/generate")
async def generate(
    body: GenerateIn,
    _: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_session),
):
    """Generate the missing exercises of a day. `force` first deletes the day's
    exercises nobody has answered yet (answered ones are kept)."""
    deleted = 0
    if body.force:
        answered = exists().where(Attempt.exercise_id == Exercise.id)
        result = await session.execute(
            delete(Exercise).where(Exercise.date == body.date, ~answered)
        )
        deleted = result.rowcount or 0  # type: ignore[attr-defined]
        await session.commit()
    if body.mode == "batch":
        run = await batch.submit_batch(session, body.date)
    else:
        run = await service.generate_day_sync(session, body.date, job="sync")
    return {"deleted": deleted, "run": cron_dict(run) if run else None}


@router.get("/cron-runs")
async def cron_runs(
    limit: int = Query(default=30, ge=1, le=200),
    _: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(select(CronRun).order_by(CronRun.started_at.desc()).limit(limit))
    ).scalars()
    return [cron_dict(r) for r in rows]
