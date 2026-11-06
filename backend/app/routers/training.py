"""GET /training — the Entraîner tab: the bonus pack and the past days' exercises left
undone, by category, outside the day's plan (DEVIATIONS D16)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..catalog import TYPE_LABELS
from ..db import get_session
from ..services import today as today_service
from ..services.clock import today_for

router = APIRouter(tags=["training"])

TYPE_ORDER = ("brainteaser", "market_sizing", "cadrage", "business_case", "diagnostic", "fit")


@router.get("/training")
async def training(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    day = today_for(user)
    cards = await today_service.training_cards(session, user.id, day)
    counts: dict[str, dict[str, int]] = {}
    for card in cards:
        entry = counts.setdefault(card.exercise.type, {"total": 0, "done": 0})
        entry["total"] += 1
        entry["done"] += int(card.done)
    types = [
        {"type": t, "label": TYPE_LABELS.get(t, t), **counts[t]}
        for t in sorted(counts, key=lambda t: (TYPE_ORDER.index(t) if t in TYPE_ORDER else 99, t))
    ]
    return {"date": day.isoformat(), "types": types, "exercises": [c.as_dict() for c in cards]}
