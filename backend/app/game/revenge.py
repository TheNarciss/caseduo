"""Spaced repetition: an exercise scored under 60 comes back 3 days later, then
10 days later, marked "revanche", XP × 1.2 — pure."""

from __future__ import annotations

from datetime import date, timedelta

REVENGE_THRESHOLD = 60
REVENGE_DELAYS = ((1, 3), (2, 10))  # (step, days after the failed attempt)


def needs_revenge(score: int, *, kind: str, flagged: bool) -> bool:
    return kind == "main" and score < REVENGE_THRESHOLD and not flagged


def schedule(answered_on: date) -> list[tuple[int, date]]:
    return [(step, answered_on + timedelta(days=days)) for step, days in REVENGE_DELAYS]
