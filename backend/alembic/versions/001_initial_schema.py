"""Initial schema — Phase 1

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── strategy_rules ────────────────────────────────────────────────────────
    op.create_table(
        "strategy_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("version", sa.Integer, nullable=False, unique=True),
        sa.Column("rules_json", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("notes", sa.Text),
    )

    # ── social_signals (stub) ─────────────────────────────────────────────────
    op.create_table(
        "social_signals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("timestamp", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("account_handle", sa.String(100)),
        sa.Column("platform", sa.String(20)),
        sa.Column("ticker", sa.String(10)),
        sa.Column("direction", sa.String(10)),
        sa.Column("signal_type", sa.String(20)),
        sa.Column("content_summary", sa.Text),
        sa.Column("original_url", sa.Text),
        sa.Column("confidence", sa.Integer),
        sa.Column("status", sa.String(15), server_default=sa.text("'captured'")),
        sa.Column("price_at_signal", sa.Numeric(10, 2)),
        sa.Column("price_1d_later", sa.Numeric(10, 2)),
        sa.Column("price_5d_later", sa.Numeric(10, 2)),
        sa.Column("price_30d_later", sa.Numeric(10, 2)),
        sa.Column("trade_id", sa.Integer),
        sa.Column("acted", sa.Boolean, server_default=sa.text("false")),
        sa.Column("pnl", sa.Numeric(10, 2), server_default=sa.text("0")),
        sa.Column("would_have_pnl", sa.Numeric(10, 2), server_default=sa.text("0")),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )

    # ── tags ──────────────────────────────────────────────────────────────────
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
    )

    # ── trades ────────────────────────────────────────────────────────────────
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("strategy_rules_version", sa.Integer, sa.ForeignKey("strategy_rules.version")),
        # Timing
        sa.Column("entry_datetime", sa.DateTime, nullable=False),
        sa.Column("exit_datetime", sa.DateTime),
        sa.Column("status", sa.String(20), server_default=sa.text("'open'")),
        # Instrument
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("instrument_type", sa.String(20), nullable=False),
        sa.Column("sector", sa.String(50)),
        sa.Column("underlying_price_entry", sa.Numeric(10, 2)),
        sa.Column("underlying_price_exit", sa.Numeric(10, 2)),
        sa.Column("strike", sa.Numeric(10, 2)),
        sa.Column("expiry_date", sa.Date),
        sa.Column("dte_at_entry", sa.Integer),
        sa.Column("barrier_level", sa.Numeric(10, 2)),
        # Pricing
        sa.Column("entry_price", sa.Numeric(10, 4), nullable=False),
        sa.Column("exit_price", sa.Numeric(10, 4)),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("fees_entry", sa.Numeric(10, 2), server_default=sa.text("0")),
        sa.Column("fees_exit", sa.Numeric(10, 2), server_default=sa.text("0")),
        sa.Column("currency", sa.String(3), server_default=sa.text("'EUR'")),
        sa.Column("fx_rate_entry", sa.Numeric(8, 4)),
        sa.Column("fx_rate_exit", sa.Numeric(8, 4)),
        # Context
        sa.Column("news_type", sa.String(50)),
        sa.Column("news_headline", sa.Text),
        sa.Column("news_url", sa.Text),
        sa.Column("market_trend", sa.String(10)),
        sa.Column("sector_trend", sa.String(10)),
        sa.Column("vix_at_entry", sa.Numeric(5, 2)),
        sa.Column("iv_percentile", sa.Numeric(5, 2)),
        sa.Column("iv_at_entry", sa.Numeric(5, 2)),
        # Social
        sa.Column("social_signal_id", sa.Integer, sa.ForeignKey("social_signals.id")),
        sa.Column("social_source_account", sa.String(100)),
        # Pre-trade planning
        sa.Column("thesis", sa.Text, nullable=False),
        sa.Column("strategy_category", sa.String(30)),
        sa.Column("profit_target_price", sa.Numeric(10, 4)),
        sa.Column("profit_target_pct", sa.Numeric(5, 2)),
        sa.Column("stop_loss_price", sa.Numeric(10, 4)),
        sa.Column("stop_loss_pct", sa.Numeric(5, 2)),
        sa.Column("time_stop_date", sa.Date),
        # Exit
        sa.Column("exit_reason", sa.String(50)),
        # Rule compliance
        sa.Column("rules_followed", sa.JSON),
        sa.Column("rules_violated", sa.JSON),
        sa.Column("rule_compliance_score", sa.Numeric(3, 2)),
        # Post-trade
        sa.Column("notes_what_worked", sa.Text),
        sa.Column("notes_what_didnt", sa.Text),
        sa.Column("lessons_learned", sa.Text),
        sa.Column("emotional_state_entry", sa.String(20)),
        sa.Column("emotional_state_exit", sa.String(20)),
        sa.Column("would_take_again", sa.Boolean),
        # Computed
        sa.Column("gross_pnl", sa.Numeric(10, 2)),
        sa.Column("net_pnl", sa.Numeric(10, 2)),
        sa.Column("gross_pnl_pct", sa.Numeric(7, 4)),
        sa.Column("net_pnl_pct", sa.Numeric(7, 4)),
        sa.Column("duration_hours", sa.Numeric(10, 2)),
        sa.Column("max_favorable_excursion", sa.Numeric(10, 2)),
        sa.Column("max_adverse_excursion", sa.Numeric(10, 2)),
        # Meta
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
    )

    op.create_index("ix_trades_ticker", "trades", ["ticker"])
    op.create_index("ix_trades_status", "trades", ["status"])
    op.create_index("ix_trades_entry_datetime", "trades", ["entry_datetime"])

    # ── trade_tags ────────────────────────────────────────────────────────────
    op.create_table(
        "trade_tags",
        sa.Column("trade_id", sa.Integer, sa.ForeignKey("trades.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id"), primary_key=True),
    )

    # ── daily_snapshots ───────────────────────────────────────────────────────
    op.create_table(
        "daily_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("date", sa.Date, nullable=False, unique=True),
        sa.Column("portfolio_value", sa.Numeric(10, 2)),
        sa.Column("cash_balance", sa.Numeric(10, 2)),
        sa.Column("invested_value", sa.Numeric(10, 2)),
        sa.Column("unrealized_pnl", sa.Numeric(10, 2)),
        sa.Column("realized_pnl_today", sa.Numeric(10, 2)),
        sa.Column("cumulative_realized_pnl", sa.Numeric(10, 2)),
        sa.Column("num_open_positions", sa.Integer),
        sa.Column("num_trades_today", sa.Integer),
        sa.Column("vix_close", sa.Numeric(5, 2)),
        sa.Column("spy_close", sa.Numeric(10, 2)),
        sa.Column("notes", sa.Text),
    )


def downgrade() -> None:
    op.drop_table("trade_tags")
    op.drop_table("daily_snapshots")
    op.drop_index("ix_trades_entry_datetime", "trades")
    op.drop_index("ix_trades_status", "trades")
    op.drop_index("ix_trades_ticker", "trades")
    op.drop_table("trades")
    op.drop_table("tags")
    op.drop_table("social_signals")
    op.drop_table("strategy_rules")
