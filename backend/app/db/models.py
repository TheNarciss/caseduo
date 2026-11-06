"""Business tables. `users` and `oauth_account` live in app/auth (fastapi-users).

Every table the spec lists is here: exercises, attempts, daily_activity,
user_story, mock_runs, badges, user_badges, cron_runs. Plus what the
mechanics need to be stored rather than recomputed: revenge schedule, data
reveals, league weeks, and Tangent's global LLM daily cost (kill-switch).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..auth.models import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Exercise(Base):
    """One exercise of one day, shared by every account (DEVIATIONS D9).

    `slot` names its place in the day's plan (`case_market_sizing`,
    `brainteaser_1`, `mock_fit`…): UNIQUE(date, slot) makes every
    generation path idempotent, batch, sync fallback and seed alike.
    """

    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    slot: Mapped[str] = mapped_column(String(48), nullable=False)
    type: Mapped[str] = mapped_column(String(24), nullable=False)
    style: Mapped[str] = mapped_column(String(12), nullable=False, default="wavestone")
    language: Mapped[str] = mapped_column(String(2), nullable=False, default="fr")
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sector: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    parts: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    context_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    model_answer: Mapped[str] = mapped_column(Text, nullable=False)
    rubric: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    targets_weakness: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    estimated_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=5)
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    flag_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="sync")
    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cron_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cron_runs.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        UniqueConstraint("date", "slot", name="uq_exercises_date_slot"),
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_exercises_difficulty"),
        CheckConstraint(
            "type IN ('market_sizing','cadrage','business_case','diagnostic',"
            "'brainteaser','fit','cadrage_home','tech_screen')",
            name="ck_exercises_type",
        ),
    )


class Attempt(Base):
    """One graded answer. `kind`: main, retry_2min, follow_up."""

    __tablename__ = "attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="main")
    parent_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attempts.id", ondelete="SET NULL"), nullable=True
    )
    mock_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mock_runs.id", ondelete="SET NULL"), nullable=True
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_mode: Mapped[str] = mapped_column(String(8), nullable=False, default="text")
    revealed_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_revenge: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rubric_scores: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    follow_up: Mapped[str | None] = mapped_column(Text, nullable=True)
    xp_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_attempts_user_created", "user_id", "created_at"),
        Index("ix_attempts_user_local_date", "user_id", "local_date"),
        CheckConstraint("score BETWEEN 0 AND 100", name="ck_attempts_score"),
    )


class DailyActivity(Base):
    __tablename__ = "daily_activity"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    xp_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exercises_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    goal_met: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    freeze_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    day_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class UserStory(Base):
    """The candidate's career story, sent to the grader for fit answers."""

    __tablename__ = "user_story"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    story_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class MockRun(Base):
    """A chained mock interview: `fit` (6 questions, 15 min) or `full` (30 min)."""

    __tablename__ = "mock_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    mbb: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    language: Mapped[str] = mapped_column(String(2), nullable=False, default="fr")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="in_progress")
    score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    exercise_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    attempt_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    xp_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "date", "kind", name="uq_mock_runs_user_day"),)


class Badge(Base):
    __tablename__ = "badges"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)


class GoalCommitment(Base):
    """A daily XP goal held for a period (DEVIATIONS D16): it cannot move before end_date."""

    __tablename__ = "goal_commitments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    daily_xp: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    rewarded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ── Le Parcours (docs/PARCOURS.md) ─────────────────────────────────────────


class PathUnit(Base):
    """One unit of the course, loaded from content/path/units/*.json."""

    __tablename__ = "path_units"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    track: Mapped[str] = mapped_column(String(16), nullable=False, default="common")
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    symbol: Mapped[str] = mapped_column(String(40), nullable=False, default="book.fill")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class PathNode(Base):
    """One circle on the path: a lesson, a review, an applied step, a checkpoint, a legendary."""

    __tablename__ = "path_nodes"

    code: Mapped[str] = mapped_column(String(48), primary_key=True)
    unit_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("path_units.code", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    objective: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    errors: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    formats: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    items: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
    applied_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PathItem(Base):
    """One micro-exercise of the bank (validated by app/path/schema.py before insert)."""

    __tablename__ = "path_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    format: Mapped[str] = mapped_column(String(24), nullable=False)
    skill: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    unit_code: Mapped[str] = mapped_column(String(16), nullable=False)
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    lang: Mapped[str] = mapped_column(String(2), nullable=False, default="fr")
    sector: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stem: Mapped[str] = mapped_column(Text, nullable=False, default="")
    media: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="repo")
    content_hash: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    flag_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flag_note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    retired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PathProgress(Base):
    """What a user did on a node: done, best score, how many times."""

    __tablename__ = "path_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    node_code: Mapped[str] = mapped_column(
        String(48), ForeignKey("path_nodes.code", ondelete="CASCADE"), primary_key=True
    )
    best_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    times: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PathItemResult(Base):
    """One answer to one item: what review, difficulty and the badge « mauvais » read."""

    __tablename__ = "path_item_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("path_items.id", ondelete="CASCADE"), nullable=False
    )
    node_code: Mapped[str] = mapped_column(String(48), nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    first_try: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UserBadge(Base):
    __tablename__ = "user_badges"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    badge_code: Mapped[str] = mapped_column(
        String(32), ForeignKey("badges.code", ondelete="CASCADE"), primary_key=True
    )
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CronRun(Base):
    """One generation run: batch submit, its completion, a sync fallback, a seed.

    Logs what the spec asks: batch id, status, tokens in/out, cost.
    """

    __tablename__ = "cron_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job: Mapped[str] = mapped_column(String(24), nullable=False)  # batch | sync | fallback | seed
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    anthropic_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    n_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    web_searches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LLMDailyCost(Base):
    """Daily aggregate of LLM spend — drives the global kill-switch (Tangent ADR-015)."""

    __tablename__ = "llm_daily_cost"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cost_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    cumulative_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    calls_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Revenge(Base):
    """Spaced repetition: an exercise scored < 60 comes back at +3 and +10 days."""

    __tablename__ = "revenges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False
    )
    source_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attempts.id", ondelete="SET NULL"), nullable=True
    )
    step: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1 = +3 days, 2 = +10 days
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    done_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attempts.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        UniqueConstraint("user_id", "exercise_id", "step", name="uq_revenges_user_ex_step"),
        Index("ix_revenges_user_due", "user_id", "due_date"),
    )


class Reveal(Base):
    """The user asked for context_data: −5 XP if it was before answering."""

    __tablename__ = "reveals"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True
    )
    revealed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class LeagueWeek(Base):
    """One user's league for one week, with the five bots it races against."""

    __tablename__ = "league_weeks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    week_start: Mapped[date] = mapped_column(Date, primary_key=True)
    tier: Mapped[str] = mapped_column(String(8), nullable=False)
    bots: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    final_rank: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
