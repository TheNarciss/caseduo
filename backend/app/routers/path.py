"""The Parcours (docs/PARCOURS.md): GET /path, start and finish a node, flag an item."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db import get_session
from ..path import service

router = APIRouter(prefix="/path", tags=["path"])


@router.get("")
async def path(
    user: User = Depends(current_active_user), session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    return await service.view(session, user)


class StartIn(BaseModel):
    seed: int | None = None


@router.post("/nodes/{code}/start")
async def start(
    code: str,
    body: StartIn | None = None,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    node = await service.node_or_404(session, code)
    return await service.start(session, user, node, seed=body.seed if body else None)


class ResultIn(BaseModel):
    item_id: str = Field(max_length=64)
    correct: bool = False
    first_try: bool = True
    ms: int = Field(default=0, ge=0, le=3_600_000)
    response: dict[str, Any] | None = None
    transcript: str | None = Field(default=None, max_length=6000)


class CompleteIn(BaseModel):
    results: list[ResultIn] = Field(default_factory=list, max_length=40)
    attempt_id: uuid.UUID | None = None  # applied steps: the exercise attempt that counts


@router.post("/nodes/{code}/complete")
async def complete(
    code: str,
    body: CompleteIn,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    node = await service.node_or_404(session, code)
    if node.kind == "applied":
        if body.attempt_id is None:
            raise service.InvalidRequestError("attempt_id manquant pour une étape en situation.")
        return await service.complete_applied(session, user, node, body.attempt_id)
    results = [service.ItemResultIn(**r.model_dump()) for r in body.results]
    return await service.complete(session, user, node, results)


class FlagIn(BaseModel):
    note: str | None = Field(default=None, max_length=300)


@router.post("/items/{item_id}/flag")
async def flag(
    item_id: str,
    body: FlagIn | None = None,
    _: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await service.flag(session, item_id, body.note if body else None)
