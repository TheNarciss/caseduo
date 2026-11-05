"""POST /mocks, GET /mocks/{id}, POST /mocks/{id}/finish."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db import get_session
from ..services import mocks
from ..services.clock import today_for

router = APIRouter(prefix="/mocks", tags=["mocks"])


class MockStart(BaseModel):
    kind: Literal["full", "fit"]


@router.post("")
async def start_mock(
    body: MockStart,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    return await mocks.start(session, user, body.kind, today_for(user))


@router.get("/{run_id}")
async def get_mock(
    run_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    run, exercises = await mocks.get(session, user, run_id)
    return mocks.run_view(run, exercises)


@router.post("/{run_id}/finish")
async def finish_mock(
    run_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
):
    return await mocks.finish(session, user, run_id)
