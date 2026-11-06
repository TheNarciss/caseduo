"""Le Parcours (docs/PARCOURS.md): units, nodes, the item bank, per-user progress and answers.

Revision ID: 0003_path
Revises: 0002_commitments
Create Date: 2026-11-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0003_path"
down_revision = "0002_commitments"
branch_labels = None
depends_on = None

NOW = sa.text("now()")
FALSE = sa.text("false")
TRUE = sa.text("true")
ZERO = sa.text("0")
EMPTY_LIST = sa.text("'[]'::jsonb")


def upgrade() -> None:
    op.create_table(
        "path_units",
        sa.Column("code", sa.String(16), primary_key=True),
        sa.Column("order", sa.SmallInteger(), nullable=False),
        sa.Column("track", sa.String(16), nullable=False, server_default="common"),
        sa.Column("title", sa.String(80), nullable=False),
        sa.Column("subtitle", sa.String(160), nullable=False, server_default=""),
        sa.Column("symbol", sa.String(40), nullable=False, server_default="book.fill"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_table(
        "path_nodes",
        sa.Column("code", sa.String(48), primary_key=True),
        sa.Column(
            "unit_code",
            sa.String(16),
            sa.ForeignKey("path_units.code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("title", sa.String(80), nullable=False),
        sa.Column("objective", sa.String(240), nullable=False, server_default=""),
        sa.Column("errors", JSONB(), nullable=False, server_default=EMPTY_LIST),
        sa.Column("formats", JSONB(), nullable=False, server_default=EMPTY_LIST),
        sa.Column("items", sa.SmallInteger(), nullable=False, server_default=sa.text("10")),
        sa.Column("applied_type", sa.String(24), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=TRUE),
    )
    op.create_table(
        "path_items",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("format", sa.String(24), nullable=False),
        sa.Column("skill", sa.String(48), nullable=False),
        sa.Column("unit_code", sa.String(16), nullable=False),
        sa.Column("difficulty", sa.SmallInteger(), nullable=False),
        sa.Column("lang", sa.String(2), nullable=False, server_default="fr"),
        sa.Column("sector", sa.String(32), nullable=True),
        sa.Column("stem", sa.Text(), nullable=False, server_default=""),
        sa.Column("media", JSONB(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("tags", JSONB(), nullable=False, server_default=EMPTY_LIST),
        sa.Column("source", sa.String(16), nullable=False, server_default="repo"),
        sa.Column("content_hash", sa.String(16), nullable=False, server_default=""),
        sa.Column("flag_count", sa.Integer(), nullable=False, server_default=ZERO),
        sa.Column("flag_note", sa.String(300), nullable=True),
        sa.Column("retired", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index("ix_path_items_skill", "path_items", ["skill"])
    op.create_table(
        "path_progress",
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "node_code",
            sa.String(48),
            sa.ForeignKey("path_nodes.code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("best_score", sa.SmallInteger(), nullable=False, server_default=ZERO),
        sa.Column("times", sa.Integer(), nullable=False, server_default=ZERO),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("user_id", "node_code"),
    )
    op.create_table(
        "path_item_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "item_id",
            sa.String(64),
            sa.ForeignKey("path_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_code", sa.String(48), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("first_try", sa.Boolean(), nullable=False, server_default=TRUE),
        sa.Column("ms", sa.Integer(), nullable=False, server_default=ZERO),
        sa.Column("response", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index("ix_path_item_results_user_item", "path_item_results", ["user_id", "item_id"])
    op.create_index("ix_path_item_results_user_created", "path_item_results", ["user_id", "created_at"])


def downgrade() -> None:
    for table in ("path_item_results", "path_progress", "path_items", "path_nodes", "path_units"):
        op.drop_table(table)
