"""Goal commitments (DEVIATIONS D16): a daily XP goal held for 7, 14 or 30 days, locked until
its last day, and the badge that rewards a kept one.

Revision ID: 0002_commitments
Revises: 0001_initial
Create Date: 2026-11-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0002_commitments"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

BADGE = {
    "code": "commitment_kept",
    "name": "Parole tenue",
    "description": "Un engagement tenu du premier au dernier jour.",
    "symbol": "hand.raised.fill",
    "sort_order": 15,
}


def upgrade() -> None:
    op.create_table(
        "goal_commitments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("daily_xp", sa.SmallInteger(), nullable=False),
        sa.Column("days", sa.SmallInteger(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("rewarded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    )
    op.create_index(
        "ix_goal_commitments_user_end", "goal_commitments", ["user_id", "end_date"]
    )
    badges = sa.table(
        "badges",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("symbol", sa.String),
        sa.column("sort_order", sa.SmallInteger),
    )
    op.bulk_insert(badges, [BADGE])


def downgrade() -> None:
    op.execute("DELETE FROM user_badges WHERE badge_code = 'commitment_kept'")
    op.execute("DELETE FROM badges WHERE code = 'commitment_kept'")
    op.drop_index("ix_goal_commitments_user_end", table_name="goal_commitments")
    op.drop_table("goal_commitments")
