"""User table — SQLAlchemy 2.0, fastapi-users base (same as Tangent).

`SQLAlchemyBaseUserTableUUID` brings id / email / hashed_password / flags.
CaseDuo adds the fields the spec puts on `users` (streak, XP, league,
APNs token…) and the per-user settings the Profile screen edits.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Boolean, Date, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .oauth_models import OAuthAccount


DEFAULT_TIMEZONE = "Asia/Singapore"


class Base(DeclarativeBase):
    """Common SQLAlchemy base for every table of the project."""


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    # Nullable: an Apple-only account has no password (Tangent ADR-014).
    hashed_password: Mapped[str | None] = mapped_column(  # type: ignore[assignment]
        String(1024), nullable=True
    )
    display_name: Mapped[str | None] = mapped_column(String(64), default=None)
    timezone: Mapped[str] = mapped_column(String(64), default=DEFAULT_TIMEZONE)
    daily_goal_xp: Mapped[int] = mapped_column(Integer, default=50)

    # Streak (app/game/streak.py). `streak_last_date` is the last local day
    # the streak covers: goal met, or bridged by a freeze.
    streak_current: Mapped[int] = mapped_column(Integer, default=0)
    streak_longest: Mapped[int] = mapped_column(Integer, default=0)
    streak_freezes: Mapped[int] = mapped_column(Integer, default=2)
    streak_last_date: Mapped[date | None] = mapped_column(Date, default=None)
    freeze_notice_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    perfect_week_until: Mapped[date | None] = mapped_column(Date, default=None)

    xp_total: Mapped[int] = mapped_column(Integer, default=0)
    league: Mapped[str] = mapped_column(String(16), default="bronze")

    # Push (DEVIATIONS D5): one device, the last one that registered.
    apns_token: Mapped[str | None] = mapped_column(String(200), default=None)
    apns_environment: Mapped[str | None] = mapped_column(String(16), default=None)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sounds_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_active_date: Mapped[date | None] = mapped_column(Date, default=None)
    last_push_date: Mapped[date | None] = mapped_column(Date, default=None)
    push_disengaged: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined", cascade="all, delete-orphan"
    )

    @property
    def has_password(self) -> bool:
        return bool(self.hashed_password)
