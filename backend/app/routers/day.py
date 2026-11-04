"""GET /widget (widget and icon badge) and GET /day/summary (end-of-day screen)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User, current_active_user
from ..catalog import LEAGUE_LABELS
from ..db import get_session
from ..db.models import Attempt
from ..game.weakness import criteria_stats
from ..services import progress, summary_hooks
from ..services import streak as streak_service
from ..services import today as today_service
from ..services.clock import today_for

router = APIRouter(tags=["day"])


@router.get("/widget")
async def widget(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    day = today_for(user)
    await streak_service.rollover(session, user, day)
    daily = await progress.daily_row(session, user, day)
    cards = await today_service.build_cards(session, user.id, day)
    status = (
        "extended_today" if daily.goal_met else ("at_risk" if user.streak_current > 0 else "safe")
    )
    await session.commit()
    return {
        "date": day.isoformat(),
        "streak": user.streak_current,
        "status": status,
        "remaining": today_service.remaining(cards),
        "xp_today": daily.xp_earned,
        "goal_xp": progress.goal_for(user, day),
    }


@router.get("/day/summary")
async def day_summary(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    day = today_for(user)
    await streak_service.rollover(session, user, day)
    daily = await progress.daily_row(session, user, day)
    scores = (
        await session.execute(
            select(Attempt.rubric_scores).where(
                Attempt.user_id == user.id,
                Attempt.local_date == day,
                Attempt.kind.in_(("main", "follow_up")),
            )
        )
    ).scalars()
    stats = criteria_stats(scores)
    weakest = stats[0] if stats and stats[0].average < 2 else None
    line = (
        f"Point faible du jour : {weakest.label[:1].lower()}{weakest.label[1:]}."
        if weakest
        else "Aucun point faible marqué aujourd'hui."
    )
    rank = await summary_hooks.league_rank(session, user, day)
    view = {
        "date": day.isoformat(),
        "streak": await streak_service.view(
            session, user, day, daily.goal_met, consume_notice=False
        ),
        "xp_today": daily.xp_earned,
        "goal": {
            "target_xp": progress.goal_for(user, day),
            "xp_today": daily.xp_earned,
            "met": daily.goal_met,
        },
        "exercises_done": daily.exercises_done,
        "league_tier": user.league,
        "league_tier_label": LEAGUE_LABELS.get(user.league, user.league),
        "league_rank": rank,
        "weakest_criterion": weakest.as_dict() if weakest else None,
        "line": line,
    }
    await session.commit()
    return view
