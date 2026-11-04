"""GET /league, GET /badges."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..db import get_session
from ..services import badges, leagues

router = APIRouter(tags=["league"])


@router.get("/league")
async def league(
    user: User = Depends(current_active_user), session: AsyncSession = Depends(get_session)
):
    view = await leagues.view(session, user)
    await session.commit()
    return view


@router.get("/badges")
async def list_badges(
    user: User = Depends(current_active_user), session: AsyncSession = Depends(get_session)
):
    return await badges.listing(session, user)
