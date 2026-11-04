"""The weekly league of a user: created on first look, closed Sunday 23:00 local."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from ..catalog import LEAGUE_LABELS
from ..db.models import DailyActivity, LeagueWeek
from ..game import badges as badge_rules
from ..game import leagues as rules
from . import badges as badge_service
from .clock import now_for, tz_of

CLOSE_AT = time(23, 0)  # Sunday evening


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def ends_at(user: User, start: date) -> datetime:
    return datetime.combine(start + timedelta(days=6), CLOSE_AT, tzinfo=tz_of(user))


async def week_xp(session: AsyncSession, user: User, start: date) -> int:
    stmt = select(func.coalesce(func.sum(DailyActivity.xp_earned), 0)).where(
        DailyActivity.user_id == user.id,
        DailyActivity.date >= start,
        DailyActivity.date <= start + timedelta(days=6),
    )
    return int((await session.execute(stmt)).scalar() or 0)


async def get_week(session: AsyncSession, user: User, start: date) -> LeagueWeek:
    row = await session.get(LeagueWeek, (user.id, start))
    if row is None:
        row = LeagueWeek(
            user_id=user.id,
            week_start=start,
            tier=user.league,
            bots=rules.generate_bots(str(user.id), start, user.league),
        )
        session.add(row)
        await session.flush()
    return row


def _progress(user: User, start: date, now: datetime) -> tuple[int, float]:
    local = now.astimezone(tz_of(user))
    index = (local.date() - start).days
    if index >= 7 or local >= ends_at(user, start):
        return 7, 1.0
    seconds = local.hour * 3600 + local.minute * 60 + local.second
    return max(0, index), seconds / 86400


async def standings(
    session: AsyncSession, user: User, row: LeagueWeek, now: datetime | None = None
) -> list[rules.Member]:
    now = now or datetime.now(UTC)
    index, fraction = _progress(user, row.week_start, now)
    me = user.display_name or "Toi"
    return rules.standings(
        me, await week_xp(session, user, row.week_start), row.bots, index, fraction
    )


async def close_due_weeks(
    session: AsyncSession, user: User, now: datetime | None = None
) -> list[dict]:
    """Close every past week not closed yet (Sunday 23:00 local passed). New badges."""
    now = now or datetime.now(UTC)
    rows = (
        await session.execute(
            select(LeagueWeek)
            .where(LeagueWeek.user_id == user.id, LeagueWeek.closed_at.is_(None))
            .order_by(LeagueWeek.week_start)
        )
    ).scalars()
    new_badges: list[dict] = []
    for row in rows:
        if now < ends_at(user, row.week_start):
            continue
        ranking = await standings(session, user, row, now)
        rank = next(m.rank for m in ranking if m.is_me)
        result = rules.outcome(rank, row.tier)
        row.final_rank, row.outcome, row.closed_at = rank, result, now
        user.league = rules.next_tier(row.tier, result)
        if result == "promoted":
            new_badges += await badge_service.award(
                session, user, badge_rules.for_league(user.league)
            )
    return new_badges


async def view(session: AsyncSession, user: User, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    await close_due_weeks(session, user, now)
    start = week_start(now_for(user, now).date())
    row = await get_week(session, user, start)
    ranking = await standings(session, user, row, now)
    previous = await session.get(LeagueWeek, (user.id, start - timedelta(days=7)))
    return {
        "tier": row.tier,
        "tier_label": LEAGUE_LABELS.get(row.tier, row.tier),
        "week_start": start.isoformat(),
        "ends_at": ends_at(user, start).isoformat(),
        "members": [
            {"name": m.name, "xp": m.xp, "is_me": m.is_me, "rank": m.rank} for m in ranking
        ],
        "promote_top": rules.PROMOTE_TOP,
        "relegate_bottom": rules.RELEGATE_BOTTOM,
        "last_outcome": previous.outcome if previous else None,
    }


async def my_rank(session: AsyncSession, user: User) -> tuple[int, int, int]:
    """(rank, size, xp this week) for /today and the end-of-day screen."""
    now = datetime.now(UTC)
    start = week_start(now_for(user, now).date())
    row = await get_week(session, user, start)
    ranking = await standings(session, user, row, now)
    me = next(m for m in ranking if m.is_me)
    return me.rank, len(ranking), me.xp
