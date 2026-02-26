"""Add portfolio positions and history tables — Phase 2

Revision ID: 002
Revises: 001
Create Date: 2026-02-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── positions ──────────────────────────────────────────────────────────
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ib_con_id", sa.Integer, nullable=True),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("instrument_type", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("avg_cost", sa.Numeric(10, 4)),
        sa.Column("market_price", sa.Numeric(10, 4)),
        sa.Column("market_value", sa.Numeric(10, 2)),
        sa.Column("unrealized_pnl", sa.Numeric(10, 2)),
        sa.Column("realized_pnl", sa.Numeric(10, 2)),
        sa.Column("currency", sa.String(3), server_default=sa.text("'USD'")),
        sa.Column("strike", sa.Numeric(10, 2)),
        sa.Column("expiry", sa.Date),
        sa.Column("option_type", sa.String(4)),
        sa.Column("sector", sa.String(50)),
        sa.Column("source", sa.String(10), server_default=sa.text("'manual'")),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("notes", sa.Text),
        sa.Column("last_updated", sa.DateTime, server_default=sa.text("now()")),
    )
    op.create_index("ix_positions_ticker", "positions", ["ticker"])
    op.create_index("ix_positions_ib_con_id", "positions", ["ib_con_id"])

    # ── portfolio_history ──────────────────────────────────────────────────
    op.create_table(
        "portfolio_history",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("timestamp", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("total_nav", sa.Numeric(10, 2)),
        sa.Column("cash_balance", sa.Numeric(10, 2)),
        sa.Column("invested_value", sa.Numeric(10, 2)),
        sa.Column("unrealized_pnl", sa.Numeric(10, 2)),
        sa.Column("margin_used", sa.Numeric(10, 2)),
        sa.Column("buying_power", sa.Numeric(10, 2)),
    )


def downgrade() -> None:
    op.drop_table("portfolio_history")
    op.drop_index("ix_positions_ib_con_id", "positions")
    op.drop_index("ix_positions_ticker", "positions")
    op.drop_table("positions")
