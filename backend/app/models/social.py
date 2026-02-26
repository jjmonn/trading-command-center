"""
Social signal model — stub for Phase 1.
Full implementation (tracked_accounts, sentiment_snapshots, Alpha Score) in Phase 4.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.database import Base


class SocialSignal(Base):
    __tablename__ = "social_signals"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    account_handle = Column(String(100))
    platform = Column(String(20))
    ticker = Column(String(10), index=True)
    direction = Column(String(10))          # bullish, bearish, neutral
    signal_type = Column(String(20))        # idea, flow_confirm, sentiment, technical, macro, catalyst
    content_summary = Column(Text)
    original_url = Column(Text)
    confidence = Column(Integer)
    status = Column(String(15), default="captured")

    # Price tracking (auto-populated by background job)
    price_at_signal = Column(Numeric(10, 2))
    price_1d_later = Column(Numeric(10, 2))
    price_5d_later = Column(Numeric(10, 2))
    price_30d_later = Column(Numeric(10, 2))

    # Outcome
    trade_id = Column(Integer)              # FK to trades.id — set in Phase 4
    acted = Column(Boolean, default=False)
    pnl = Column(Numeric(10, 2), default=0)
    would_have_pnl = Column(Numeric(10, 2), default=0)

    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
