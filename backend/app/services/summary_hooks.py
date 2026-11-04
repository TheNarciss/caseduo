"""League position for the end-of-day screen; the leagues feature fills it in."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User


async def league_rank(session: AsyncSession, user: User, day: date) -> int | None:
    return None
