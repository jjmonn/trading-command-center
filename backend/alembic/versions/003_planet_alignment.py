"""Add Planet Alignment tables — Phase 3

Revision ID: 003
Revises: 002
Create Date: 2026-05-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ticker", sa.String(10), nullable=False, unique=True),
        sa.Column("added_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("notes", sa.Text),
        sa.Column("custom_weights", sa.JSON),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1")),
    )
    op.create_index("ix_watchlist_ticker", "watchlist", ["ticker"])

    op.create_table(
        "factor_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("factor_name", sa.String(30), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("raw_data", sa.JSON, nullable=False),
        sa.Column("score", sa.Integer),
        sa.Column("verdict", sa.String(10)),
        sa.Column("explanation", sa.Text),
        sa.Column("source", sa.String(20)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("ticker", "factor_name", "snapshot_date",
                            name="uq_factor_snapshot"),
    )
    op.create_index("ix_factor_ticker_date", "factor_snapshots",
                    ["ticker", "snapshot_date"])

    op.create_table(
        "alignment_scores",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("composite_score", sa.Integer),
        sa.Column("verdict", sa.String(20)),
        sa.Column("factor_scores", sa.JSON),
        sa.Column("warnings", sa.JSON),
        sa.Column("llm_synthesis", sa.Text),
        sa.Column("llm_synthesis_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("ticker", "snapshot_date",
                            name="uq_alignment_score"),
    )
    op.create_index("ix_alignment_ticker_date", "alignment_scores",
                    ["ticker", "snapshot_date"])


def downgrade() -> None:
    op.drop_index("ix_alignment_ticker_date", "alignment_scores")
    op.drop_table("alignment_scores")
    op.drop_index("ix_factor_ticker_date", "factor_snapshots")
    op.drop_table("factor_snapshots")
    op.drop_index("ix_watchlist_ticker", "watchlist")
    op.drop_table("watchlist")
