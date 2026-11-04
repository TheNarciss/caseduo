"""The daily_activity row of a user and a day, created on first touch."""

from __future__ import annotations

from datetime import date

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from ..db.models import DailyActivity


async def daily_row(session: AsyncSession, user: User, day: date) -> DailyActivity:
    stmt = (
        pg_insert(DailyActivity)
        .values(user_id=user.id, date=day)
        .on_conflict_do_nothing(index_elements=["user_id", "date"])
    )
    await session.execute(stmt)
    row = await session.get(DailyActivity, (user.id, day), populate_existing=True)
    assert row is not None
    return row
