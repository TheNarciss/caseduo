"""League position for the end-of-day screen."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from . import leagues


async def league_rank(session: AsyncSession, user: User, day: date) -> int | None:
    rank, _, _ = await leagues.my_rank(session, user)
    return rank
