"""GET /exercises/{id}, POST /exercises/{id}/reveal."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db import get_session
from ..db.models import Attempt, Exercise, Reveal, Revenge
from ..errors import NotFoundError
from ..game.xp import REVEAL_PENALTY
from ..services.clock import today_for
from .serializers import exercise_detail

router = APIRouter(prefix="/exercises", tags=["exercises"])


async def _exercise(session: AsyncSession, exercise_id: uuid.UUID) -> Exercise:
    ex = await session.get(Exercise, exercise_id)
    if ex is None:
        raise NotFoundError("Exercice introuvable.")
    return ex


@router.get("/{exercise_id}")
async def get_exercise(
    exercise_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    ex = await _exercise(session, exercise_id)
    attempts = (
        (
            await session.execute(
                select(Attempt)
                .where(Attempt.user_id == user.id, Attempt.exercise_id == ex.id)
                .order_by(Attempt.created_at)
            )
        )
        .scalars()
        .all()
    )
    revealed = await session.get(Reveal, (user.id, ex.id)) is not None
    revenge = (
        await session.execute(
            select(Revenge.id).where(
                Revenge.user_id == user.id,
                Revenge.exercise_id == ex.id,
                Revenge.due_date <= today_for(user),
                Revenge.done_attempt_id.is_(None),
            )
        )
    ).first()
    return exercise_detail(ex, list(attempts), revealed=revealed, is_revenge=revenge is not None)


@router.post("/{exercise_id}/reveal")
async def reveal_data(
    exercise_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """The candidate asks the interviewer for the figures: −5 XP if before answering."""
    ex = await _exercise(session, exercise_id)
    answered = (
        await session.execute(
            select(Attempt.id).where(
                Attempt.user_id == user.id, Attempt.exercise_id == ex.id, Attempt.kind == "main"
            )
        )
    ).first()
    await session.execute(
        pg_insert(Reveal)
        .values(user_id=user.id, exercise_id=ex.id)
        .on_conflict_do_nothing(index_elements=["user_id", "exercise_id"])
    )
    await session.commit()
    penalty = 0 if (answered or ex.style == "mbb") else REVEAL_PENALTY
    return {"context_data": ex.context_data or {}, "xp_penalty": penalty}
