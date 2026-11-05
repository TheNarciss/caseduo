"""What a generation needs to know besides the plan: the owner's weaknesses,
first-week easy mode, and the titles already used (anti-duplicate, 60 days)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from ..db.models import Attempt, Exercise
from ..game.weakness import CriterionStat, weakest_criteria

WEAKNESS_WINDOW_DAYS = 14
DUPLICATE_WINDOW_DAYS = 60
EASY_DAYS = 7


@dataclass
class GenerationContext:
    weaknesses: list[CriterionStat] = field(default_factory=list)
    easy_mode: bool = False
    recent_titles: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    @property
    def weakness_keys(self) -> list[str]:
        return [w.key for w in self.weaknesses]


async def owner(session: AsyncSession) -> User | None:
    """The account whose progress drives the shared daily content (DEVIATIONS D9)."""
    email = os.getenv("OWNER_EMAIL", "").strip()
    if email:
        stmt = select(User).where(User.email == email)  # type: ignore[arg-type]
        found = (await session.execute(stmt)).unique().scalar_one_or_none()
        if found:
            return found
    for clause in (User.is_superuser.is_(True), User.is_active.is_(True)):  # type: ignore[attr-defined]
        stmt = select(User).where(clause).order_by(User.created_at).limit(1)
        found = (await session.execute(stmt)).unique().scalar_one_or_none()
        if found:
            return found
    return None


async def user_weaknesses(
    session: AsyncSession, user_id, today: date, days: int = WEAKNESS_WINDOW_DAYS
) -> list[CriterionStat]:
    since = today - timedelta(days=days)
    stmt = (
        select(Attempt.rubric_scores)
        .join(Exercise, Exercise.id == Attempt.exercise_id)
        .where(
            Attempt.user_id == user_id,
            Attempt.local_date > since,
            Attempt.kind.in_(("main", "follow_up")),
            Exercise.flagged.is_(False),
        )
    )
    rows = (await session.execute(stmt)).scalars().all()
    return weakest_criteria(rows)


async def build_context(session: AsyncSession, day: date) -> GenerationContext:
    ctx = GenerationContext()
    me = await owner(session)
    if me is not None:
        tz = ZoneInfo(me.timezone or "Asia/Singapore")
        created = me.created_at.astimezone(tz).date() if me.created_at else day
        ctx.easy_mode = (day - created).days < EASY_DAYS
        ctx.weaknesses = await user_weaknesses(session, me.id, day)
    since = day - timedelta(days=DUPLICATE_WINDOW_DAYS)
    stmt = select(Exercise.type, Exercise.title, Exercise.sector).where(
        Exercise.date >= since, Exercise.date < day
    )
    for type_, title, sector in (await session.execute(stmt)).all():
        ctx.recent_titles.setdefault(type_, []).append((title, sector))
    return ctx
