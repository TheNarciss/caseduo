"""GET /attempts, GET /attempts/{id}."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db import get_session
from ..db.models import Attempt, Exercise
from ..errors import NotFoundError
from .serializers import attempt_full, attempt_summary

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.get("")
async def list_attempts(
    limit: int = Query(default=30, ge=1, le=200),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(Attempt, Exercise)
            .join(Exercise, Exercise.id == Attempt.exercise_id)
            .where(Attempt.user_id == user.id)
            .order_by(Attempt.created_at.desc())
            .limit(limit)
        )
    ).all()
    return [attempt_summary(a, ex) for a, ex in rows]


@router.get("/{attempt_id}")
async def get_attempt(
    attempt_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    attempt = await session.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise NotFoundError("Tentative introuvable.")
    ex = await session.get(Exercise, attempt.exercise_id)
    assert ex is not None
    return attempt_full(attempt, ex)
