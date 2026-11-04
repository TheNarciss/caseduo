"""Extension points of /today (streak rollover, league rank…), filled by later features."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User


async def before_today(session: AsyncSession, user: User, day: date) -> None:
    return None


async def after_today(session: AsyncSession, user: User, day: date, view: dict[str, Any]) -> None:
    return None
