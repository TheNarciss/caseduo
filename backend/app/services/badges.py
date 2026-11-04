"""Awarding badges (idempotent) and listing them."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from ..db.models import Attempt, Badge, Exercise, UserBadge


def badge_dict(b: Badge, earned_at=None) -> dict[str, Any]:
    return {
        "code": b.code,
        "name": b.name,
        "description": b.description,
        "symbol": b.symbol,
        "earned_at": earned_at.isoformat() if earned_at else None,
    }


async def award(session: AsyncSession, user: User, codes: set[str]) -> list[dict[str, Any]]:
    """Insert the badges not yet earned; returns the new ones."""
    if not codes:
        return []
    have = set(
        (
            await session.execute(select(UserBadge.badge_code).where(UserBadge.user_id == user.id))
        ).scalars()
    )
    new = codes - have
    if not new:
        return []
    for code in new:
        await session.execute(
            pg_insert(UserBadge)
            .values(user_id=user.id, badge_code=code)
            .on_conflict_do_nothing(index_elements=["user_id", "badge_code"])
        )
    rows = (await session.execute(select(Badge).where(Badge.code.in_(new)))).scalars()
    return [badge_dict(b) for b in sorted(rows, key=lambda b: b.sort_order)]


async def fit_answer_count(session: AsyncSession, user: User) -> int:
    stmt = (
        select(func.count())
        .select_from(Attempt)
        .join(Exercise, Exercise.id == Attempt.exercise_id)
        .where(Attempt.user_id == user.id, Attempt.kind == "main", Exercise.type == "fit")
    )
    return int((await session.execute(stmt)).scalar() or 0)


async def listing(session: AsyncSession, user: User) -> list[dict[str, Any]]:
    stmt = select(UserBadge.badge_code, UserBadge.earned_at).where(UserBadge.user_id == user.id)
    earned: dict[str, Any] = {code: at for code, at in (await session.execute(stmt)).all()}
    rows = (await session.execute(select(Badge).order_by(Badge.sort_order))).scalars()
    return [badge_dict(b, earned.get(b.code)) for b in rows]
