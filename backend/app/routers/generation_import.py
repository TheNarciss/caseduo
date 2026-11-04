"""Generation by a Claude Code scheduled task (DEVIATIONS D13).

Like the Thales project's daily scheduled task: every night a fresh Claude
Code session (claude.ai cloud) asks this backend what tomorrow still
lacks, writes each exercise itself — prompts/generate.md as its system
prompt, web search included — and sends the JSON back here. The backend
validates it exactly like an API generation (schema, rubric, sources,
anti-duplicate) and inserts it; a rejected exercise comes back as a 422
with the reason, so the session can fix it and resend (its 2 retries).

Auth: `Authorization: Bearer <GENERATION_IMPORT_TOKEN>` — a machine token,
separate from user sessions. The routes answer 404 when it is not set.
"""

from __future__ import annotations

import hmac
import os
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..db.models import CronRun
from ..errors import AppError, ConflictError, InvalidRequestError, NotFoundError
from ..generation import request, schema, service
from ..generation.planner import WEEKDAY_FR
from ..llm import cost_tracker, prompts
from ..llm.messages import normalize_url

router = APIRouter(prefix="/generation", tags=["generation"])

JOB = "claude_code"


class Unauthorized(AppError):
    status_code = 401


def require_token(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("GENERATION_IMPORT_TOKEN", "").strip()
    if not expected:
        raise NotFoundError("Import de génération désactivé.")
    given = (authorization or "").removeprefix("Bearer ").strip()
    if not hmac.compare_digest(given.encode(), expected.encode()):
        raise Unauthorized("Jeton d'import invalide.")


def default_day() -> date:
    return cost_tracker.today_jobs_tz() + timedelta(days=1)


async def run_for(session: AsyncSession, day: date) -> CronRun:
    """One cron_runs row per night (job = claude_code), reused by every import."""
    stmt = (
        select(CronRun)
        .where(CronRun.job == JOB, CronRun.target_date == day, CronRun.status == "running")
        .order_by(CronRun.started_at.desc())
        .limit(1)
    )
    run = (await session.execute(stmt)).scalar_one_or_none()
    if run is None:
        run = CronRun(job=JOB, target_date=day, status="running", model="claude-code", errors=[])
        session.add(run)
        await session.flush()
    return run


@router.get("/plan", dependencies=[Depends(require_token)])
async def plan(
    day: date | None = Query(default=None, alias="date"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """What to write for `date` (default: tomorrow): the system prompt and, per missing
    slot, the exact user message an API generation would send."""
    day = day or default_day()
    day_plan, ctx = await service.plan_for(session, day)
    missing = await service.missing_slots(session, day_plan)
    run = await run_for(session, day)
    run.n_requests = max(run.n_requests, len(missing) + run.n_succeeded)
    await session.commit()
    return {
        "date": day.isoformat(),
        "weekday": WEEKDAY_FR[day.weekday()],
        "sector": day_plan.sector,
        "system_prompt": prompts.load("generate"),
        "done": sorted(await service.existing_slots(session, day)),
        "slots": [
            {
                "slot": s.slot,
                "type": s.type,
                "style": s.style,
                "language": s.language,
                "difficulty": s.difficulty,
                "sector": s.sector,
                "web_search": s.web_search,
                "parts": s.parts,
                "user_message": request.user_message(day_plan, s, ctx),
            }
            for s in missing
        ],
    }


class ImportIn(BaseModel):
    date: date
    slot: str = Field(min_length=1, max_length=48)
    exercise: dict[str, Any]
    search_urls: list[str] | None = Field(
        default=None, description="URLs the web search really returned (to mark sources verified)"
    )


@router.post("/import", dependencies=[Depends(require_token)])
async def import_exercise(
    body: ImportIn, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    day_plan, ctx = await service.plan_for(session, body.date)
    spec = day_plan.slot(body.slot)
    if spec is None:
        raise NotFoundError(f"Le slot {body.slot!r} n'existe pas le {body.date}.")
    if body.slot in await service.existing_slots(session, body.date):
        raise ConflictError(f"{body.slot} existe déjà pour le {body.date}.")
    run = await run_for(session, body.date)
    try:
        fields = schema.validate(
            body.exercise,
            spec,
            search_urls={normalize_url(u) for u in body.search_urls}
            if body.search_urls is not None
            else None,
            weaknesses=ctx.weakness_keys,
            recent_titles=ctx.recent_titles.get(spec.type),
        )
    except schema.GenerationInvalid as exc:
        run.errors = [
            *run.errors,
            {"slot": body.slot, "attempt": "claude_code", "error": str(exc)[:500]},
        ]
        await session.commit()
        raise InvalidRequestError(f"Exercice refusé : {exc}") from exc
    inserted = await service.insert_exercise(
        session, body.date, body.slot, fields, mode=JOB, run_id=run.id, model="claude-code"
    )
    run.n_succeeded += int(inserted)
    await session.commit()
    remaining = [s.slot for s in await service.missing_slots(session, day_plan)]
    return {"inserted": inserted, "slot": body.slot, "remaining": remaining}


class FinishIn(BaseModel):
    date: date
    summary: str | None = Field(default=None, max_length=4000)


@router.post("/finish", dependencies=[Depends(require_token)])
async def finish(body: FinishIn, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    """Close the night's run. Whatever is still missing is left to the 05:30 fallback."""
    day_plan, _ = await service.plan_for(session, body.date)
    missing = [s.slot for s in await service.missing_slots(session, day_plan)]
    run = await run_for(session, body.date)
    run.n_failed = len(missing)
    run.status = "ended" if not missing else ("partial" if run.n_succeeded else "failed")
    run.finished_at = datetime.now(UTC)
    if body.summary:
        run.errors = [*run.errors, {"summary": body.summary}]
    await session.commit()
    return {"status": run.status, "inserted": run.n_succeeded, "missing": missing}
