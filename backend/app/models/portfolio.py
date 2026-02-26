"""
Portfolio & Position models — Module 3.
Tracks positions (synced from IB or manually entered) and portfolio history.
"""
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Integer, JSON, Numeric, String, Text,
)
from sqlalchemy.sql import func

from app.database import Base


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    ib_con_id = Column(Integer, nullable=True)  # IB contract ID (null for manual)

    ticker = Column(String(10), nullable=False, index=True)
    instrument_type = Column(String(20), nullable=False)
    # stock | call_option | put_option | call_warrant | put_warrant | turbo_long | turbo_short

    quantity = Column(Numeric(10, 2), nullable=False)
    avg_cost = Column(Numeric(10, 4))
    market_price = Column(Numeric(10, 4))
    market_value = Column(Numeric(10, 2))
    unrealized_pnl = Column(Numeric(10, 2))
    realized_pnl = Column(Numeric(10, 2))
    currency = Column(String(3), default="USD")

    # Option/warrant specifics
    strike = Column(Numeric(10, 2))
    expiry = Column(Date)
    option_type = Column(String(4))  # CALL / PUT

    # Metadata
    sector = Column(String(50))
    source = Column(String(10), default="manual")  # ib | manual
    is_active = Column(Boolean, default=True)
    notes = Column(Text)

    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PortfolioHistory(Base):
    __tablename__ = "portfolio_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    total_nav = Column(Numeric(10, 2))
    cash_balance = Column(Numeric(10, 2))
    invested_value = Column(Numeric(10, 2))
    unrealized_pnl = Column(Numeric(10, 2))
    margin_used = Column(Numeric(10, 2))
    buying_power = Column(Numeric(10, 2))
