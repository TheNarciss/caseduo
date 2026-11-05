"""Streak and freezes — pure, tested (timezones, midnight, missed days).

- The streak counts consecutive local days with the daily goal met.
- `last_date` is the last day the streak covers: a met goal, or a missed
  day bridged by a freeze.
- Freezes: 2 to start, +1 every 7 days of streak, at most 3, used
  automatically on a missed day. A frozen day keeps the streak, it does not
  add to it.
- A perfect week: goal met every day from Monday to Sunday, no freeze.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta

MAX_FREEZES = 3
FREEZE_EVERY_DAYS = 7


@dataclass(frozen=True)
class StreakState:
    current: int = 0
    longest: int = 0
    freezes: int = 2
    last_date: date | None = None


@dataclass(frozen=True)
class Rollover:
    state: StreakState
    frozen_days: tuple[date, ...] = ()
    broken: bool = False


@dataclass(frozen=True)
class GoalMet:
    state: StreakState
    extended: bool = False
    freeze_earned: bool = False


def close_missed_days(state: StreakState, today: date) -> Rollover:
    """Settle every past day the streak does not cover yet (before `today`)."""
    if (
        state.current == 0
        or state.last_date is None
        or state.last_date >= today - timedelta(days=1)
    ):
        return Rollover(state)
    frozen: list[date] = []
    day = state.last_date + timedelta(days=1)
    current, freezes, last = state.current, state.freezes, state.last_date
    while day < today:
        if freezes > 0:
            freezes -= 1
            last = day
            frozen.append(day)
        else:
            return Rollover(
                replace(state, current=0, freezes=freezes, last_date=last),
                tuple(frozen),
                broken=True,
            )
        day += timedelta(days=1)
    return Rollover(replace(state, current=current, freezes=freezes, last_date=last), tuple(frozen))


def on_goal_met(state: StreakState, day: date) -> GoalMet:
    """The goal of `day` was just met. Call `close_missed_days` first."""
    if state.last_date == day:
        return GoalMet(state)
    current = state.current + 1 if state.last_date == day - timedelta(days=1) else 1
    freezes = state.freezes
    earned = False
    if current % FREEZE_EVERY_DAYS == 0 and freezes < MAX_FREEZES:
        freezes += 1
        earned = True
    new = StreakState(
        current=current,
        longest=max(state.longest, current),
        freezes=freezes,
        last_date=day,
    )
    return GoalMet(new, extended=True, freeze_earned=earned)


def is_perfect_week(days: dict[date, tuple[bool, bool]], sunday: date) -> bool:
    """`days[d] = (goal_met, freeze_used)`; Monday→Sunday all met, no freeze."""
    if sunday.weekday() != 6:
        return False
    monday = sunday - timedelta(days=6)
    for i in range(7):
        met, frozen = days.get(monday + timedelta(days=i), (False, False))
        if not met or frozen:
            return False
    return True
