"""Initial schema: users, exercises, attempts, daily activity, story, mocks,
badges, cron runs, LLM daily cost, revenges, reveals, league weeks.

Hand-written (Tangent convention): every NOT NULL column with a Python
default also gets a server default, so rows inserted outside the ORM
(psql, scripts) stay valid. Seeds the badge catalogue.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-04
"""

from __future__ import annotations

import fastapi_users_db_sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

NOW = sa.text("now()")
FALSE = sa.text("false")
TRUE = sa.text("true")
ZERO = sa.text("0")
EMPTY_LIST = sa.text("'[]'::jsonb")
EMPTY_OBJ = sa.text("'{}'::jsonb")


def _int(name: str, default: str = "0") -> sa.Column:
    return sa.Column(name, sa.Integer(), nullable=False, server_default=sa.text(default))


def _uuid_fk(name: str, target: str, ondelete: str, nullable: bool = False) -> sa.Column:
    return sa.Column(
        name, UUID(as_uuid=True), sa.ForeignKey(target, ondelete=ondelete), nullable=nullable
    )


BADGES = [
    # code, name, description, SF Symbol, order
    ("first_case", "Premier case", "Tu as répondu à ton premier case.", "briefcase.fill", 1),
    ("streak_3", "3 jours", "Trois jours d'affilée.", "flame", 2),
    ("streak_7", "Une semaine", "Sept jours d'affilée.", "flame.fill", 3),
    ("streak_10", "10 jours", "Dix jours d'affilée : le cap où l'habitude tient.", "flame.circle.fill", 4),
    ("streak_30", "30 jours", "Un mois sans casser la série. Icône spéciale débloquée.", "crown.fill", 5),
    ("perfect_week", "Semaine parfaite", "Objectif atteint chaque jour du lundi au dimanche, sans freeze.", "star.circle.fill", 6),
    ("score_90", "90+", "Un case noté 90 ou plus.", "rosette", 7),
    ("revenge_won", "Revanche", "Un exercice raté, repris et réussi.", "arrow.uturn.up.circle.fill", 8),
    ("follow_up_held", "Pas coincé", "Une relance tenue avec 80 ou plus.", "bubble.left.and.exclamationmark.bubble.right.fill", 9),
    ("mock_done", "Mock bouclé", "Un mock entretien complet, de bout en bout.", "person.wave.2.fill", 10),
    ("cadrage_home_done", "Cadrage rendu", "Un cadrage à domicile rendu en 5 slides.", "doc.richtext.fill", 11),
    ("fit_10", "Fit solide", "Dix questions de fit travaillées.", "person.text.rectangle.fill", 12),
    ("league_silver", "Argent", "Promu en ligue Argent.", "medal", 13),
    ("league_gold", "Or", "Promu en ligue Or.", "medal.fill", 14),
]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", fastapi_users_db_sqlalchemy.generics.GUID(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=TRUE),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("display_name", sa.String(length=64), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Singapore"),
        _int("daily_goal_xp", "50"),
        _int("streak_current"),
        _int("streak_longest"),
        _int("streak_freezes", "2"),
        sa.Column("streak_last_date", sa.Date(), nullable=True),
        sa.Column("freeze_notice_pending", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("perfect_week_until", sa.Date(), nullable=True),
        _int("xp_total"),
        sa.Column("league", sa.String(length=16), nullable=False, server_default="bronze"),
        sa.Column("apns_token", sa.String(length=200), nullable=True),
        sa.Column("apns_environment", sa.String(length=16), nullable=True),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=TRUE),
        sa.Column("sounds_enabled", sa.Boolean(), nullable=False, server_default=TRUE),
        sa.Column("last_active_date", sa.Date(), nullable=True),
        sa.Column("last_push_date", sa.Date(), nullable=True),
        sa.Column("push_disengaged", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "oauth_account",
        sa.Column("id", fastapi_users_db_sqlalchemy.generics.GUID(), primary_key=True),
        sa.Column(
            "user_id",
            fastapi_users_db_sqlalchemy.generics.GUID(),
            sa.ForeignKey("users.id", ondelete="cascade"),
            nullable=False,
        ),
        sa.Column("oauth_name", sa.String(length=100), nullable=False),
        sa.Column("access_token", sa.String(length=1024), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=True),
        sa.Column("refresh_token", sa.String(length=1024), nullable=True),
        sa.Column("account_id", sa.String(length=320), nullable=False),
        sa.Column("account_email", sa.String(length=320), nullable=False),
        sa.UniqueConstraint("oauth_name", "account_id", name="uq_oauth_account_provider_id"),
    )
    op.create_index("ix_oauth_account_account_id", "oauth_account", ["account_id"])
    op.create_index("ix_oauth_account_oauth_name", "oauth_account", ["oauth_name"])

    op.create_table(
        "cron_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job", sa.String(length=24), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("anthropic_batch_id", sa.String(length=64), nullable=True, unique=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        _int("n_requests"),
        _int("n_succeeded"),
        _int("n_failed"),
        _int("input_tokens"),
        _int("output_tokens"),
        _int("cache_read_tokens"),
        _int("cache_write_tokens"),
        _int("web_searches"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default=ZERO),
        sa.Column("errors", JSONB(), nullable=False, server_default=EMPTY_LIST),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cron_runs_target_date", "cron_runs", ["target_date"])
    op.create_index("ix_cron_runs_started_at", "cron_runs", ["started_at"])

    op.create_table(
        "exercises",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("slot", sa.String(length=48), nullable=False),
        sa.Column("type", sa.String(length=24), nullable=False),
        sa.Column("style", sa.String(length=12), nullable=False, server_default="wavestone"),
        sa.Column("language", sa.String(length=2), nullable=False, server_default="fr"),
        sa.Column("difficulty", sa.SmallInteger(), nullable=False),
        sa.Column("sector", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("parts", JSONB(), nullable=True),
        sa.Column("context_data", JSONB(), nullable=False, server_default=EMPTY_OBJ),
        sa.Column("model_answer", sa.Text(), nullable=False),
        sa.Column("rubric", JSONB(), nullable=False),
        sa.Column("sources", JSONB(), nullable=False, server_default=EMPTY_LIST),
        sa.Column("targets_weakness", JSONB(), nullable=False, server_default=EMPTY_LIST),
        sa.Column("estimated_minutes", sa.SmallInteger(), nullable=False, server_default="5"),
        sa.Column("flagged", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("flag_note", sa.Text(), nullable=True),
        sa.Column("generation_mode", sa.String(length=16), nullable=False, server_default="sync"),
        sa.Column("model_used", sa.String(length=64), nullable=True),
        _uuid_fk("cron_run_id", "cron_runs.id", "SET NULL", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint("date", "slot", name="uq_exercises_date_slot"),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_exercises_difficulty"),
        sa.CheckConstraint(
            "type IN ('market_sizing','cadrage','business_case','diagnostic',"
            "'brainteaser','fit','cadrage_home','tech_screen')",
            name="ck_exercises_type",
        ),
    )
    op.create_index("ix_exercises_date", "exercises", ["date"])

    op.create_table(
        "mock_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        _uuid_fk("user_id", "users.id", "CASCADE"),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("mbb", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("language", sa.String(length=2), nullable=False, server_default="fr"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="in_progress"),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("exercise_ids", JSONB(), nullable=False, server_default=EMPTY_LIST),
        sa.Column("attempt_ids", JSONB(), nullable=False, server_default=EMPTY_LIST),
        _int("xp_earned"),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "date", "kind", name="uq_mock_runs_user_day"),
    )
    op.create_index("ix_mock_runs_user_id", "mock_runs", ["user_id"])

    op.create_table(
        "attempts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        _uuid_fk("user_id", "users.id", "CASCADE"),
        _uuid_fk("exercise_id", "exercises.id", "CASCADE"),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="main"),
        _uuid_fk("parent_attempt_id", "attempts.id", "SET NULL", nullable=True),
        _uuid_fk("mock_run_id", "mock_runs.id", "SET NULL", nullable=True),
        sa.Column("answer_text", sa.Text(), nullable=False),
        _int("duration_seconds"),
        sa.Column("input_mode", sa.String(length=8), nullable=False, server_default="text"),
        sa.Column("revealed_data", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("is_revenge", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("rubric_scores", JSONB(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("follow_up", sa.Text(), nullable=True),
        _int("xp_earned"),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("model_used", sa.String(length=64), nullable=True),
        _int("input_tokens"),
        _int("output_tokens"),
        _int("cache_read_tokens"),
        _int("cache_write_tokens"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default=ZERO),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="ck_attempts_score"),
    )
    op.create_index("ix_attempts_user_created", "attempts", ["user_id", "created_at"])
    op.create_index("ix_attempts_user_local_date", "attempts", ["user_id", "local_date"])

    op.create_table(
        "daily_activity",
        _uuid_fk("user_id", "users.id", "CASCADE"),
        sa.Column("date", sa.Date(), nullable=False),
        _int("xp_earned"),
        _int("exercises_done"),
        sa.Column("goal_met", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("freeze_used", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("day_complete", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("user_id", "date"),
    )

    op.create_table(
        "user_story",
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("story_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )

    op.create_table(
        "badges",
        sa.Column("code", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default=ZERO),
    )
    op.create_table(
        "user_badges",
        _uuid_fk("user_id", "users.id", "CASCADE"),
        sa.Column(
            "badge_code",
            sa.String(length=32),
            sa.ForeignKey("badges.code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("user_id", "badge_code"),
    )

    op.create_table(
        "llm_daily_cost",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cost_date", sa.Date(), nullable=False),
        sa.Column("cumulative_cost_usd", sa.Float(), nullable=False, server_default=ZERO),
        _int("calls_count"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index("ix_llm_daily_cost_cost_date", "llm_daily_cost", ["cost_date"], unique=True)

    op.create_table(
        "revenges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        _uuid_fk("user_id", "users.id", "CASCADE"),
        _uuid_fk("exercise_id", "exercises.id", "CASCADE"),
        _uuid_fk("source_attempt_id", "attempts.id", "SET NULL", nullable=True),
        sa.Column("step", sa.SmallInteger(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        _uuid_fk("done_attempt_id", "attempts.id", "SET NULL", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint("user_id", "exercise_id", "step", name="uq_revenges_user_ex_step"),
    )
    op.create_index("ix_revenges_user_due", "revenges", ["user_id", "due_date"])

    op.create_table(
        "reveals",
        _uuid_fk("user_id", "users.id", "CASCADE"),
        _uuid_fk("exercise_id", "exercises.id", "CASCADE"),
        sa.Column("revealed_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("user_id", "exercise_id"),
    )

    op.create_table(
        "league_weeks",
        _uuid_fk("user_id", "users.id", "CASCADE"),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("tier", sa.String(length=8), nullable=False),
        sa.Column("bots", JSONB(), nullable=False, server_default=EMPTY_LIST),
        sa.Column("final_rank", sa.SmallInteger(), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("user_id", "week_start"),
    )

    badges = sa.table(
        "badges",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("symbol", sa.String),
        sa.column("sort_order", sa.SmallInteger),
    )
    op.bulk_insert(
        badges,
        [
            {"code": c, "name": n, "description": d, "symbol": s, "sort_order": o}
            for c, n, d, s, o in BADGES
        ],
    )


def downgrade() -> None:
    for table in (
        "league_weeks",
        "reveals",
        "revenges",
        "llm_daily_cost",
        "user_badges",
        "badges",
        "user_story",
        "daily_activity",
        "attempts",
        "mock_runs",
        "exercises",
        "cron_runs",
        "oauth_account",
        "users",
    ):
        op.drop_table(table)
