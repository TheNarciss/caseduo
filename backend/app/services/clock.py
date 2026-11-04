"""The user's local date: every daily mechanic (goal, streak, cards) is local."""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..auth import User
from ..auth.models import DEFAULT_TIMEZONE


def tz_of(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.timezone or DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(DEFAULT_TIMEZONE)


def now_for(user: User, now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)).astimezone(tz_of(user))


def today_for(user: User, now: datetime | None = None) -> date:
    return now_for(user, now).date()


def first_week(user: User, day: date) -> bool:
    created = user.created_at.astimezone(tz_of(user)).date() if user.created_at else day
    return (day - created).days < 7
