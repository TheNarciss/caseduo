"""GET /today — everything the Home screen shows, in one call."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..catalog import LEAGUE_LABELS
from ..db import get_session
from ..db.models import DailyActivity, Exercise, MockRun
from ..generation.planner import mock_is_mbb, mock_kind, mock_language
from ..services import commitments, hooks, progress
from ..services import streak as streak_service
from ..services import today as today_service
from ..services.clock import first_week, today_for

router = APIRouter(tags=["today"])


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


async def xp_between(session: AsyncSession, user: User, start: date, end: date) -> int:
    stmt = select(func.coalesce(func.sum(DailyActivity.xp_earned), 0)).where(
        DailyActivity.user_id == user.id, DailyActivity.date >= start, DailyActivity.date <= end
    )
    return int((await session.execute(stmt)).scalar() or 0)


async def mock_info(session: AsyncSession, user: User, day: date) -> dict[str, Any] | None:
    kind = mock_kind(day)
    if kind is None:
        return None
    prefix = "mock_fit_set" if kind == "fit" else "mock_"
    stmt = (
        select(func.count())
        .select_from(Exercise)
        .where(Exercise.date == day, Exercise.slot.startswith(prefix))
    )
    if not (await session.execute(stmt)).scalar():
        return None
    run = (
        await session.execute(
            select(MockRun).where(
                MockRun.user_id == user.id, MockRun.date == day, MockRun.kind == kind
            )
        )
    ).scalar_one_or_none()
    return {
        "kind": kind,
        "mbb": kind == "full" and mock_is_mbb(day),
        "language": mock_language(day) if kind == "full" else "fr",
        "done": run is not None and run.status == "finished",
        "run_id": str(run.id) if run else None,
    }


async def build_today(session: AsyncSession, user: User) -> dict[str, Any]:
    day = today_for(user)
    await streak_service.rollover(session, user, day)
    await hooks.before_today(session, user, day)
    daily = await progress.daily_row(session, user, day)
    cards = await today_service.build_cards(session, user.id, day)
    streak = await streak_service.view(session, user, day, daily.goal_met, consume_notice=True)
    view: dict[str, Any] = {
        "date": day.isoformat(),
        "weekday": day.weekday(),
        "timezone": user.timezone,
        "streak": streak,
        "goal": {
            "target_xp": progress.goal_for(user, day),
            "xp_today": daily.xp_earned,
            "met": daily.goal_met,
        },
        "remaining": today_service.remaining(cards),
        "day_complete": daily.day_complete,
        "easy_mode": first_week(user, day),
        "mock": await mock_info(session, user, day),
        "cards": [c.as_dict() for c in cards],
        "unlocks": {
            "streak30_icon": user.streak_longest >= 30,
            "perfect_week_until": (
                user.perfect_week_until.isoformat()
                if user.perfect_week_until and user.perfect_week_until >= day
                else None
            ),
        },
        "league": {
            "tier": user.league,
            "tier_label": LEAGUE_LABELS.get(user.league, user.league),
            "rank": None,
            "size": None,
            "xp_week": await xp_between(session, user, week_start(day), day),
        },
        "is_admin": user.is_superuser,
        "commitment": await commitments.for_screen(session, user, day),
    }
    await hooks.after_today(session, user, day, view)
    await session.commit()
    return view


@router.get("/today")
async def today(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    return await build_today(session, user)
