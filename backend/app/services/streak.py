"""Streak bookkeeping on the user row: rollover at each visit and every hour,
increment when the goal is met, perfect week, the view the app shows."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from ..db.models import DailyActivity
from ..game import streak as rules
from .progress_rows import daily_row

PERFECT_WEEK_DAYS = 7


def state_of(user: User) -> rules.StreakState:
    return rules.StreakState(
        current=user.streak_current,
        longest=user.streak_longest,
        freezes=user.streak_freezes,
        last_date=user.streak_last_date,
    )


def store(user: User, state: rules.StreakState) -> None:
    user.streak_current = state.current
    user.streak_longest = state.longest
    user.streak_freezes = state.freezes
    user.streak_last_date = state.last_date


async def rollover(session: AsyncSession, user: User, today: date) -> rules.Rollover:
    result = rules.close_missed_days(state_of(user), today)
    if result.state != state_of(user):
        store(user, result.state)
    for day in result.frozen_days:
        (await daily_row(session, user, day)).freeze_used = True
    if result.frozen_days:
        user.freeze_notice_pending = True
    return result


async def goal_met(session: AsyncSession, user: User, day: date) -> rules.GoalMet:
    result = rules.on_goal_met(state_of(user), day)
    store(user, result.state)
    return result


async def check_perfect_week(session: AsyncSession, user: User, day: date) -> bool:
    if day.weekday() != 6:
        return False
    rows = (
        await session.execute(
            select(DailyActivity).where(
                DailyActivity.user_id == user.id,
                DailyActivity.date >= day - timedelta(days=6),
                DailyActivity.date <= day,
            )
        )
    ).scalars()
    days = {r.date: (r.goal_met, r.freeze_used) for r in rows}
    if rules.is_perfect_week(days, day):
        user.perfect_week_until = day + timedelta(days=PERFECT_WEEK_DAYS)
        return True
    return False


async def recent_freezes(session: AsyncSession, user: User, today: date) -> list[str]:
    rows = (
        await session.execute(
            select(DailyActivity.date).where(
                DailyActivity.user_id == user.id,
                DailyActivity.freeze_used.is_(True),
                DailyActivity.date >= today - timedelta(days=30),
            )
        )
    ).scalars()
    return sorted(d.isoformat() for d in rows)


async def view(
    session: AsyncSession, user: User, today: date, goal_met_today: bool, *, consume_notice: bool
) -> dict[str, Any]:
    if goal_met_today:
        status = "extended_today"
    elif user.streak_current > 0:
        status = "at_risk"
    else:
        status = "safe"
    just_used = bool(user.freeze_notice_pending) if consume_notice else False
    if consume_notice:
        user.freeze_notice_pending = False
    return {
        "current": user.streak_current,
        "longest": user.streak_longest,
        "freezes": user.streak_freezes,
        "status": status,
        "freeze_used_on": await recent_freezes(session, user, today),
        "freeze_just_used": just_used,
    }
