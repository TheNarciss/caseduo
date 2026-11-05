"""Which push, if any, a user gets now — pure, tested.

- Streak saver at 20:00 local if the goal is not met: "Ta série de {n} jours
  se termine dans 4 h". Never more than one push a day.
- After 7 days without activity: one last message, then silence until the
  user comes back.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

STREAK_SAVER_AT = time(20, 0)
WINDOW_MINUTES = 15  # the tick runs every 15 minutes
DISENGAGE_AFTER_DAYS = 7


@dataclass(frozen=True)
class Push:
    kind: str  # streak_saver | disengage
    title: str
    body: str


@dataclass(frozen=True)
class PushState:
    notifications_enabled: bool
    has_token: bool
    disengaged: bool
    last_push_date: date | None
    last_active_date: date | None
    streak_current: int
    goal_met_today: bool


def in_window(local_now: datetime) -> bool:
    start = datetime.combine(local_now.date(), STREAK_SAVER_AT, tzinfo=local_now.tzinfo)
    return 0 <= (local_now - start).total_seconds() < WINDOW_MINUTES * 60


def decide(state: PushState, local_now: datetime) -> Push | None:
    today = local_now.date()
    if not (state.notifications_enabled and state.has_token) or state.disengaged:
        return None
    if state.last_push_date == today or not in_window(local_now):
        return None
    inactive = (today - state.last_active_date).days if state.last_active_date is not None else None
    if inactive is not None and inactive >= DISENGAGE_AFTER_DAYS:
        return Push(
            "disengage",
            "CaseDuo",
            "On arrête les rappels pour l'instant. Reviens quand tu veux.",
        )
    if state.streak_current > 0 and not state.goal_met_today:
        n = state.streak_current
        jours = "jour" if n == 1 else "jours"
        return Push("streak_saver", "CaseDuo", f"Ta série de {n} {jours} se termine dans 4 h")
    return None
