"""Extension points of /today: league position."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from . import leagues


async def before_today(session: AsyncSession, user: User, day: date) -> None:
    await leagues.close_due_weeks(session, user)


async def after_today(session: AsyncSession, user: User, day: date, view: dict[str, Any]) -> None:
    rank, size, xp = await leagues.my_rank(session, user)
    view["league"].update({"tier": user.league, "rank": rank, "size": size, "xp_week": xp})
