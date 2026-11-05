"""Badges earned by a finished mock."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from ..db.models import MockRun
from ..services import badges


async def after_mock(session: AsyncSession, user: User, run: MockRun) -> list[dict]:
    return await badges.award(session, user, {"mock_done"})
