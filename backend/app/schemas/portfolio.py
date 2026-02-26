"""
Pydantic schemas for portfolio/positions — Module 3.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Position schemas ────────────────────────────────────────────────────────

class PositionCreate(BaseModel):
    """Create a position manually (for non-IB holdings like Saxo warrants)."""
    ticker: str = Field(..., min_length=1, max_length=10)
    instrument_type: str
    quantity: Decimal
    avg_cost: Optional[Decimal] = None
    market_price: Optional[Decimal] = None
    currency: str = "USD"
    strike: Optional[Decimal] = None
    expiry: Optional[date] = None
    option_type: Optional[str] = None  # CALL / PUT
    sector: Optional[str] = None
    notes: Optional[str] = None


class PositionUpdate(BaseModel):
    """Partial update for a position."""
    quantity: Optional[Decimal] = None
    avg_cost: Optional[Decimal] = None
    market_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    currency: Optional[str] = None
    strike: Optional[Decimal] = None
    expiry: Optional[date] = None
    option_type: Optional[str] = None
    sector: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class PositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ib_con_id: Optional[int] = None
    ticker: str
    instrument_type: str
    quantity: Decimal
    avg_cost: Optional[Decimal] = None
    market_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    currency: Optional[str] = None
    strike: Optional[Decimal] = None
    expiry: Optional[date] = None
    option_type: Optional[str] = None
    sector: Optional[str] = None
    source: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None
    last_updated: Optional[datetime] = None

    # Computed in the router (not stored)
    pnl_pct: Optional[float] = None
    dte: Optional[int] = None
    weight_pct: Optional[float] = None


# ─── Portfolio history ───────────────────────────────────────────────────────

class PortfolioHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    total_nav: Optional[Decimal] = None
    cash_balance: Optional[Decimal] = None
    invested_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    margin_used: Optional[Decimal] = None
    buying_power: Optional[Decimal] = None


# ─── Portfolio summary (computed, not a DB model) ────────────────────────────

class PortfolioSummary(BaseModel):
    total_nav: float
    cash_balance: float
    invested_value: float
    unrealized_pnl: float
    total_long_exposure: float
    total_short_exposure: float
    net_exposure: float
    cash_pct: float
    leverage_ratio: float
    num_positions: int
    risk_alerts: list[str]


class ExposureBreakdown(BaseModel):
    label: str
    value: float
    pct: float


class PortfolioDashboard(BaseModel):
    summary: PortfolioSummary
    positions: list[PositionResponse]
    by_sector: list[ExposureBreakdown]
    by_instrument: list[ExposureBreakdown]
    by_currency: list[ExposureBreakdown]
    history: list[PortfolioHistoryResponse]


# ─── IB connection status ────────────────────────────────────────────────────

class IBStatus(BaseModel):
    connected: bool
    host: str
    port: int
    message: str
