"""GET /history — score curves per type, recurring weaknesses, streak calendar."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..catalog import EXERCISE_TYPES, TYPE_LABELS
from ..db import get_session
from ..db.models import Attempt, DailyActivity, Exercise, MockRun
from ..game.weakness import criteria_stats, weakest_criteria
from ..generation.context import WEAKNESS_WINDOW_DAYS
from ..services.clock import today_for
from .serializers import attempt_summary

router = APIRouter(tags=["history"])


def month_start(day: date) -> date:
    return day.replace(day=1)


@router.get("/history")
async def history(
    days: int = Query(default=90, ge=7, le=365),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    today = today_for(user)
    since = today - timedelta(days=days)
    rows = (
        await session.execute(
            select(Attempt, Exercise)
            .join(Exercise, Exercise.id == Attempt.exercise_id)
            .where(Attempt.user_id == user.id, Attempt.local_date > since)
            .order_by(Attempt.created_at)
        )
    ).all()

    series: dict[str, list[dict[str, Any]]] = {}
    for attempt, ex in rows:
        if attempt.kind != "main":
            continue
        series.setdefault(ex.type, []).append(
            {"date": attempt.local_date.isoformat(), "score": attempt.score}
        )

    graded = [(a, ex) for a, ex in rows if a.kind in ("main", "follow_up") and not ex.flagged]
    recent_14 = [
        a.rubric_scores
        for a, _ in graded
        if a.local_date > today - timedelta(days=WEAKNESS_WINDOW_DAYS)
    ]
    recent_30 = [a.rubric_scores for a, _ in graded if a.local_date > today - timedelta(days=30)]

    first_month = month_start(month_start(today) - timedelta(days=1))
    calendar = (
        await session.execute(
            select(DailyActivity)
            .where(DailyActivity.user_id == user.id, DailyActivity.date >= first_month)
            .order_by(DailyActivity.date)
        )
    ).scalars()

    mocks = (
        await session.execute(
            select(MockRun)
            .where(MockRun.user_id == user.id, MockRun.status == "finished")
            .order_by(MockRun.date)
        )
    ).scalars()

    return {
        "series": [
            {"type": t, "label": TYPE_LABELS[t], "points": series[t]}
            for t in EXERCISE_TYPES
            if t in series
        ],
        "weaknesses": [w.as_dict() for w in weakest_criteria(recent_14)],
        "criteria": [c.as_dict() for c in criteria_stats(recent_30)],
        "calendar": [
            {
                "date": d.date.isoformat(),
                "goal_met": d.goal_met,
                "freeze_used": d.freeze_used,
                "xp": d.xp_earned,
            }
            for d in calendar
        ],
        "recent_attempts": [attempt_summary(a, ex) for a, ex in reversed(rows[-20:])],
        "mocks": [
            {"id": str(m.id), "date": m.date.isoformat(), "kind": m.kind, "score": m.score}
            for m in mocks
        ],
    }
