"""Push and streak jobs (every 15 min / every hour), one session per run."""

from __future__ import annotations

import logging

from sqlalchemy import select

from ..auth import User
from ..db import async_session_factory
from ..services import leagues
from ..services import streak as streak_service
from ..services import today as today_service
from ..services.clock import now_for, today_for
from ..services.progress_rows import daily_row
from . import apns, rules

logger = logging.getLogger(__name__)


async def job_streak_rollover() -> None:
    """Settle missed days for everyone (freezes applied even if the app stays closed)."""
    async with async_session_factory() as session:
        try:
            stmt = select(User).where(User.is_active.is_(True))  # type: ignore[attr-defined]
            users = (await session.execute(stmt)).unique().scalars().all()
            for user in users:
                await streak_service.rollover(session, user, today_for(user))
            await session.commit()
        except Exception:
            logger.exception("Streak rollover failed")
            await session.rollback()


async def job_push_tick() -> None:
    if not apns.is_configured():
        return
    async with async_session_factory() as session:
        try:
            stmt = select(User).where(
                User.is_active.is_(True),  # type: ignore[attr-defined]
                User.apns_token.is_not(None),
                User.notifications_enabled.is_(True),
            )
            for user in (await session.execute(stmt)).unique().scalars().all():
                await _maybe_push(session, user)
            await session.commit()
        except Exception:
            logger.exception("Push tick failed")
            await session.rollback()


async def _maybe_push(session, user: User) -> None:
    local_now = now_for(user)
    if not rules.in_window(local_now):
        return
    day = local_now.date()
    await streak_service.rollover(session, user, day)
    daily = await daily_row(session, user, day)
    state = rules.PushState(
        notifications_enabled=user.notifications_enabled,
        has_token=bool(user.apns_token),
        disengaged=user.push_disengaged,
        last_push_date=user.last_push_date,
        last_active_date=user.last_active_date,
        streak_current=user.streak_current,
        goal_met_today=daily.goal_met,
    )
    push = rules.decide(state, local_now)
    if push is None:
        return
    cards = await today_service.build_cards(session, user.id, day)
    result = await apns.send(
        user.apns_token or "",
        push.title,
        push.body,
        environment=user.apns_environment,
        badge=today_service.remaining(cards),
        collapse_id=f"{push.kind}-{day.isoformat()}",
    )
    user.last_push_date = day  # one attempt a day, delivered or not
    if push.kind == "disengage":
        user.push_disengaged = True
    if result.token_invalid:
        user.apns_token = None
    logger.info("Push %s to user %s: %s", push.kind, user.id, result.status)


async def job_close_leagues() -> None:
    """Promotion / relegation once Sunday 23:00 local has passed."""
    async with async_session_factory() as session:
        try:
            stmt = select(User).where(User.is_active.is_(True))  # type: ignore[attr-defined]
            for user in (await session.execute(stmt)).unique().scalars().all():
                await leagues.close_due_weeks(session, user)
            await session.commit()
        except Exception:
            logger.exception("League close failed")
            await session.rollback()
