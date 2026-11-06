"""Goal commitments (DEVIATIONS D16): the daily XP goal is a promise over a period.

"Je m'engage" means something: the goal cannot move for 7, 14 or 30 days. The day
screen then tracks the promise day by day (kept, frozen, missed), and a commitment
kept to its last day earns the badge « Parole tenue ».
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from ..db.models import DailyActivity, GoalCommitment
from ..errors import ConflictError
from . import badges as badge_service

XP_CHOICES = (30, 50, 80)
DAYS_CHOICES = (7, 14, 30)
BADGE = "commitment_kept"
# An ended commitment stays on the day screen this long, for its summary.
SUMMARY_GRACE_DAYS = 7


async def active(session: AsyncSession, user: User, day: date) -> GoalCommitment | None:
    stmt = (
        select(GoalCommitment)
        .where(
            GoalCommitment.user_id == user.id,
            GoalCommitment.start_date <= day,
            GoalCommitment.end_date >= day,
        )
        .order_by(GoalCommitment.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def latest(session: AsyncSession, user: User) -> GoalCommitment | None:
    stmt = (
        select(GoalCommitment)
        .where(GoalCommitment.user_id == user.id)
        .order_by(GoalCommitment.end_date.desc(), GoalCommitment.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def start(
    session: AsyncSession, user: User, day: date, *, daily_xp: int, days: int
) -> GoalCommitment:
    """A new commitment from today. Refused while one is running. Not committed."""
    current = await active(session, user, day)
    if current is not None:
        raise ConflictError(
            f"Engagement en cours jusqu'au {current.end_date.strftime('%d/%m')} : "
            "il ne bouge pas avant."
        )
    commitment = GoalCommitment(
        id=uuid.uuid4(),
        user_id=user.id,
        daily_xp=daily_xp,
        days=days,
        start_date=day,
        end_date=day + timedelta(days=days - 1),
    )
    session.add(commitment)
    user.daily_goal_xp = daily_xp
    session.add(user)
    return commitment


async def guard_goal_change(session: AsyncSession, user: User, day: date) -> None:
    """PATCH /me cannot move the goal while a commitment runs."""
    current = await active(session, user, day)
    if current is not None:
        raise ConflictError(
            f"Ton engagement court jusqu'au {current.end_date.strftime('%d/%m')} : "
            "l'objectif ne bouge pas avant."
        )


async def view(
    session: AsyncSession, user: User, commitment: GoalCommitment, day: date
) -> dict[str, Any]:
    """The promise day by day, up to today."""
    last = min(day, commitment.end_date)
    rows = (
        await session.execute(
            select(DailyActivity).where(
                DailyActivity.user_id == user.id,
                DailyActivity.date >= commitment.start_date,
                DailyActivity.date <= last,
            )
        )
    ).scalars()
    by_day = {r.date: r for r in rows}
    days: list[dict[str, Any]] = []
    met = frozen = missed = 0
    for i in range(commitment.days):
        d = commitment.start_date + timedelta(days=i)
        row = by_day.get(d)
        if d > last:
            state = "future"
        elif row is not None and row.goal_met:
            state, met = "met", met + 1
        elif row is not None and row.freeze_used:
            state, frozen = "frozen", frozen + 1
        elif d == day:
            state = "today"
        else:
            state, missed = "missed", missed + 1
        days.append({"date": d.isoformat(), "state": state})
    ended = day > commitment.end_date
    day_index = min(commitment.days, max(1, (day - commitment.start_date).days + 1))
    return {
        "id": str(commitment.id),
        "daily_xp": commitment.daily_xp,
        "days": commitment.days,
        "start_date": commitment.start_date.isoformat(),
        "end_date": commitment.end_date.isoformat(),
        "status": "ended" if ended else "active",
        "day_index": day_index,
        "days_met": met,
        "days_frozen": frozen,
        "days_missed": missed,
        "on_track": missed == 0,
        "kept": (missed == 0) if ended else None,
        "badge_awarded": commitment.rewarded,
        "calendar": days,
    }


async def for_screen(session: AsyncSession, user: User, day: date) -> dict[str, Any] | None:
    """The running commitment, or the last one for a week after it ended, else None."""
    commitment = await active(session, user, day)
    if commitment is None:
        commitment = await latest(session, user)
        if commitment is None or commitment.end_date < day - timedelta(days=SUMMARY_GRACE_DAYS):
            return None
    return await view(session, user, commitment, day)


async def reward_if_kept(session: AsyncSession, user: User, day: date) -> list[dict[str, Any]]:
    """The badge, once, when the last commitment ended without a missed day. Not committed."""
    commitment = await latest(session, user)
    if commitment is None or commitment.rewarded or day <= commitment.end_date:
        return []
    summary = await view(session, user, commitment, day)
    if not summary["kept"]:
        return []
    commitment.rewarded = True
    session.add(commitment)
    return await badge_service.award(session, user, {BADGE})
