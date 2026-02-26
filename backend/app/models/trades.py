from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Integer, JSON, Numeric, String, Table, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

# ─── Association table ─────────────────────────────────────────────────────────

trade_tags = Table(
    "trade_tags",
    Base.metadata,
    Column("trade_id", Integer, ForeignKey("trades.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


# ─── Strategy Rules ────────────────────────────────────────────────────────────

class StrategyRules(Base):
    __tablename__ = "strategy_rules"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(Integer, nullable=False, unique=True)
    rules_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    notes = Column(Text)


# ─── Tags ──────────────────────────────────────────────────────────────────────

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    trades = relationship("Trade", secondary=trade_tags, back_populates="tags")


# ─── Core trade table ─────────────────────────────────────────────────────────

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    strategy_rules_version = Column(Integer, ForeignKey("strategy_rules.version"), nullable=True)

    # ── Timing ────────────────────────────────────────────────────────────────
    entry_datetime = Column(DateTime, nullable=False)
    exit_datetime = Column(DateTime)
    status = Column(String(20), default="open", nullable=False)   # open | closed | expired

    # ── Instrument ────────────────────────────────────────────────────────────
    ticker = Column(String(10), nullable=False, index=True)
    instrument_type = Column(String(20), nullable=False)
    # stock | call_option | put_option | call_warrant | put_warrant | turbo_long | turbo_short
    sector = Column(String(50))
    underlying_price_entry = Column(Numeric(10, 2))
    underlying_price_exit = Column(Numeric(10, 2))
    strike = Column(Numeric(10, 2))
    expiry_date = Column(Date)
    dte_at_entry = Column(Integer)
    barrier_level = Column(Numeric(10, 2))

    # ── Pricing ───────────────────────────────────────────────────────────────
    entry_price = Column(Numeric(10, 4), nullable=False)
    exit_price = Column(Numeric(10, 4))
    quantity = Column(Integer, nullable=False)
    fees_entry = Column(Numeric(10, 2), default=0)
    fees_exit = Column(Numeric(10, 2), default=0)
    currency = Column(String(3), default="EUR")
    fx_rate_entry = Column(Numeric(8, 4))
    fx_rate_exit = Column(Numeric(8, 4))

    # ── Context at entry ──────────────────────────────────────────────────────
    news_type = Column(String(50))
    # earnings | buyback | analyst_upgrade | analyst_downgrade | geopolitical |
    # sector_news | guidance | product_launch | regulatory | technical_setup | flow_signal
    news_headline = Column(Text)
    news_url = Column(Text)
    market_trend = Column(String(10))    # bullish | bearish | neutral | choppy
    sector_trend = Column(String(10))
    vix_at_entry = Column(Numeric(5, 2))
    iv_percentile = Column(Numeric(5, 2))
    iv_at_entry = Column(Numeric(5, 2))

    # ── Social signal source ──────────────────────────────────────────────────
    social_signal_id = Column(Integer, ForeignKey("social_signals.id"), nullable=True)
    social_source_account = Column(String(100))

    # ── Pre-trade planning (required before entry) ────────────────────────────
    thesis = Column(Text, nullable=False)
    strategy_category = Column(String(30))
    # momentum_news | earnings_event | trend_swing | core_holding | flow_follow | thematic
    profit_target_price = Column(Numeric(10, 4))
    profit_target_pct = Column(Numeric(5, 2))
    stop_loss_price = Column(Numeric(10, 4))
    stop_loss_pct = Column(Numeric(5, 2))
    time_stop_date = Column(Date)

    # ── Exit details ──────────────────────────────────────────────────────────
    exit_reason = Column(String(50))
    # profit_target | stop_loss | time_stop | thesis_invalidated | trailing_stop | manual | expiry

    # ── Rule compliance ───────────────────────────────────────────────────────
    rules_followed = Column(JSON)           # list of rule IDs
    rules_violated = Column(JSON)           # list of rule IDs
    rule_compliance_score = Column(Numeric(3, 2))   # 0.0 – 1.0

    # ── Post-trade analysis ───────────────────────────────────────────────────
    notes_what_worked = Column(Text)
    notes_what_didnt = Column(Text)
    lessons_learned = Column(Text)
    emotional_state_entry = Column(String(20))
    # calm | anxious | excited | revenge | fomo | confident
    emotional_state_exit = Column(String(20))
    would_take_again = Column(Boolean)

    # ── Computed at close ─────────────────────────────────────────────────────
    gross_pnl = Column(Numeric(10, 2))
    net_pnl = Column(Numeric(10, 2))
    gross_pnl_pct = Column(Numeric(7, 4))
    net_pnl_pct = Column(Numeric(7, 4))
    duration_hours = Column(Numeric(10, 2))
    max_favorable_excursion = Column(Numeric(10, 2))
    max_adverse_excursion = Column(Numeric(10, 2))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────────────────────
    tags = relationship("Tag", secondary=trade_tags, back_populates="trades")
    social_signal = relationship("SocialSignal", foreign_keys=[social_signal_id])
    strategy_rules = relationship("StrategyRules", foreign_keys=[strategy_rules_version])


# ─── Daily portfolio snapshot ─────────────────────────────────────────────────

class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False)
    portfolio_value = Column(Numeric(10, 2))
    cash_balance = Column(Numeric(10, 2))
    invested_value = Column(Numeric(10, 2))
    unrealized_pnl = Column(Numeric(10, 2))
    realized_pnl_today = Column(Numeric(10, 2))
    cumulative_realized_pnl = Column(Numeric(10, 2))
    num_open_positions = Column(Integer)
    num_trades_today = Column(Integer)
    vix_close = Column(Numeric(5, 2))
    spy_close = Column(Numeric(10, 2))
    notes = Column(Text)
