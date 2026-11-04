"""Badges earned by a finished mock; the badges feature fills this in."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from ..db.models import MockRun


async def after_mock(session: AsyncSession, user: User, run: MockRun) -> list[dict]:
    return []
