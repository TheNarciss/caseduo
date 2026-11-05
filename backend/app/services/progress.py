"""What an attempt changes: XP, daily goal, day-complete bonus, remaining cards.

Called once per graded attempt, inside the grading transaction. The streak,
badges and revenges hook in here as they arrive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import User
from ..db.models import Attempt, Exercise
from ..game.xp import DAY_COMPLETE_BONUS, effective_goal
from . import streak as streak_service
from . import today as today_service
from .clock import first_week
from .progress_rows import daily_row


@dataclass
class ProgressResult:
    xp_today: int = 0
    goal_target: int = 50
    goal_met: bool = False
    goal_just_met: bool = False
    streak: dict[str, Any] = field(default_factory=dict)
    streak_extended: bool = False
    freeze_earned: bool = False
    day_complete: bool = False
    day_complete_bonus: int = 0
    perfect_week: bool = False
    remaining: int = 0
    new_badges: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


__all__ = ["ProgressResult", "apply_attempt", "daily_row", "goal_for"]


def goal_for(user: User, day: date) -> int:
    return effective_goal(user.daily_goal_xp, first_week=first_week(user, day))


async def apply_attempt(
    session: AsyncSession, user: User, attempt: Attempt, exercise: Exercise
) -> ProgressResult:
    day = attempt.local_date
    await streak_service.rollover(session, user, day)
    daily = await daily_row(session, user, day)
    daily.xp_earned += attempt.xp_earned
    if attempt.kind == "main":
        daily.exercises_done += 1
    user.xp_total += attempt.xp_earned
    user.last_active_date = day
    user.push_disengaged = False

    result = ProgressResult(goal_target=goal_for(user, day))
    await session.flush()

    cards = await today_service.build_cards(session, user.id, day)
    if not daily.day_complete and today_service.day_complete(cards):
        daily.day_complete = True
        daily.xp_earned += DAY_COMPLETE_BONUS
        user.xp_total += DAY_COMPLETE_BONUS
        result.day_complete_bonus = DAY_COMPLETE_BONUS

    was_met = daily.goal_met
    daily.goal_met = daily.xp_earned >= result.goal_target
    result.goal_met = daily.goal_met
    result.goal_just_met = daily.goal_met and not was_met
    if result.goal_just_met:
        met = await streak_service.goal_met(session, user, day)
        result.streak_extended = met.extended
        result.freeze_earned = met.freeze_earned
        result.perfect_week = await streak_service.check_perfect_week(session, user, day)
    result.streak = await streak_service.view(
        session, user, day, daily.goal_met, consume_notice=False
    )
    result.xp_today = daily.xp_earned
    result.day_complete = daily.day_complete
    result.remaining = today_service.remaining(cards)
    return result
