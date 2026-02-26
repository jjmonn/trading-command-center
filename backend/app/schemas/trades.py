from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ─── Enums as literals ────────────────────────────────────────────────────────

TradeStatus = str           # open | closed | expired
InstrumentType = str        # stock | call_option | put_option | call_warrant | put_warrant | turbo_long | turbo_short
NewsType = str              # earnings | buyback | analyst_upgrade | ...
MarketTrend = str           # bullish | bearish | neutral | choppy
EmotionalState = str        # calm | anxious | excited | revenge | fomo | confident
StrategyCategory = str      # momentum_news | earnings_event | trend_swing | core_holding | flow_follow | thematic
ExitReason = str            # profit_target | stop_loss | time_stop | thesis_invalidated | trailing_stop | manual | expiry


# ─── Strategy Rules ────────────────────────────────────────────────────────────

class StrategyRulesCreate(BaseModel):
    version: int
    rules_json: dict[str, Any]
    notes: Optional[str] = None


class StrategyRulesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    rules_json: dict[str, Any]
    created_at: datetime
    notes: Optional[str] = None


# ─── Trade schemas ─────────────────────────────────────────────────────────────

class TradeCreate(BaseModel):
    """Schema for logging a new (open) trade. Enforces pre-trade planning rules."""

    # Timing
    entry_datetime: datetime = Field(default_factory=datetime.utcnow)

    # Instrument (required)
    ticker: str = Field(..., min_length=1, max_length=10)
    instrument_type: InstrumentType
    sector: Optional[str] = None
    underlying_price_entry: Optional[Decimal] = None
    strike: Optional[Decimal] = None
    expiry_date: Optional[date] = None
    dte_at_entry: Optional[int] = None
    barrier_level: Optional[Decimal] = None

    # Pricing (required)
    entry_price: Decimal = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    fees_entry: Decimal = Field(default=Decimal("0"))
    currency: str = Field(default="EUR", max_length=3)
    fx_rate_entry: Optional[Decimal] = None

    # Context
    news_type: Optional[NewsType] = None
    news_headline: Optional[str] = None
    news_url: Optional[str] = None
    market_trend: Optional[MarketTrend] = None
    sector_trend: Optional[str] = None
    vix_at_entry: Optional[Decimal] = None
    iv_percentile: Optional[Decimal] = None
    iv_at_entry: Optional[Decimal] = None

    # Social source
    social_signal_id: Optional[int] = None
    social_source_account: Optional[str] = None

    # Pre-trade planning (REQUIRED — backend enforces)
    thesis: str = Field(..., min_length=10, description="Why this trade (max 2 sentences)")
    strategy_category: Optional[StrategyCategory] = None
    profit_target_price: Optional[Decimal] = None
    profit_target_pct: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None
    stop_loss_pct: Optional[Decimal] = None
    time_stop_date: Optional[date] = None

    # Psychology (REQUIRED)
    emotional_state_entry: EmotionalState = Field(...)

    # Rule compliance
    rules_followed: Optional[list[str]] = None
    rules_violated: Optional[list[str]] = None
    rule_compliance_score: Optional[Decimal] = Field(None, ge=0, le=1)

    # Optional version reference
    strategy_rules_version: Optional[int] = None

    @field_validator("ticker")
    @classmethod
    def ticker_upper(cls, v: str) -> str:
        return v.upper().strip()

    @model_validator(mode="after")
    def exit_plan_required(self) -> "TradeCreate":
        has_target = self.profit_target_price is not None or self.profit_target_pct is not None
        has_stop = self.stop_loss_price is not None or self.stop_loss_pct is not None
        if not has_target:
            raise ValueError("profit_target_price or profit_target_pct is required before entry")
        if not has_stop:
            raise ValueError("stop_loss_price or stop_loss_pct is required before entry")
        return self


class TradeClose(BaseModel):
    """Payload for closing a trade and computing P&L."""

    exit_price: Decimal = Field(..., gt=0)
    exit_datetime: datetime = Field(default_factory=datetime.utcnow)
    fees_exit: Decimal = Field(default=Decimal("0"))
    fx_rate_exit: Optional[Decimal] = None
    exit_reason: ExitReason
    emotional_state_exit: Optional[EmotionalState] = None

    # Post-trade analysis
    notes_what_worked: Optional[str] = None
    notes_what_didnt: Optional[str] = None
    lessons_learned: Optional[str] = None
    would_take_again: Optional[bool] = None

    # MAE / MFE (optional — entered manually for now)
    max_favorable_excursion: Optional[Decimal] = None
    max_adverse_excursion: Optional[Decimal] = None


class TradeUpdate(BaseModel):
    """Partial update — all fields optional."""

    sector: Optional[str] = None
    news_type: Optional[NewsType] = None
    news_headline: Optional[str] = None
    news_url: Optional[str] = None
    market_trend: Optional[MarketTrend] = None
    sector_trend: Optional[str] = None
    vix_at_entry: Optional[Decimal] = None
    iv_percentile: Optional[Decimal] = None
    iv_at_entry: Optional[Decimal] = None
    thesis: Optional[str] = None
    strategy_category: Optional[StrategyCategory] = None
    profit_target_price: Optional[Decimal] = None
    profit_target_pct: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None
    stop_loss_pct: Optional[Decimal] = None
    time_stop_date: Optional[date] = None
    notes_what_worked: Optional[str] = None
    notes_what_didnt: Optional[str] = None
    lessons_learned: Optional[str] = None
    emotional_state_entry: Optional[EmotionalState] = None
    would_take_again: Optional[bool] = None
    rules_followed: Optional[list[str]] = None
    rules_violated: Optional[list[str]] = None
    rule_compliance_score: Optional[Decimal] = Field(None, ge=0, le=1)


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    entry_datetime: datetime
    exit_datetime: Optional[datetime] = None

    ticker: str
    instrument_type: str
    sector: Optional[str] = None
    underlying_price_entry: Optional[Decimal] = None
    underlying_price_exit: Optional[Decimal] = None
    strike: Optional[Decimal] = None
    expiry_date: Optional[date] = None
    dte_at_entry: Optional[int] = None
    barrier_level: Optional[Decimal] = None

    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    quantity: int
    fees_entry: Optional[Decimal] = None
    fees_exit: Optional[Decimal] = None
    currency: Optional[str] = None

    news_type: Optional[str] = None
    news_headline: Optional[str] = None
    market_trend: Optional[str] = None
    sector_trend: Optional[str] = None
    vix_at_entry: Optional[Decimal] = None
    iv_percentile: Optional[Decimal] = None

    thesis: str
    strategy_category: Optional[str] = None
    profit_target_price: Optional[Decimal] = None
    profit_target_pct: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None
    stop_loss_pct: Optional[Decimal] = None
    time_stop_date: Optional[date] = None

    exit_reason: Optional[str] = None
    rules_followed: Optional[list[str]] = None
    rules_violated: Optional[list[str]] = None
    rule_compliance_score: Optional[Decimal] = None

    notes_what_worked: Optional[str] = None
    notes_what_didnt: Optional[str] = None
    lessons_learned: Optional[str] = None
    emotional_state_entry: Optional[str] = None
    emotional_state_exit: Optional[str] = None
    would_take_again: Optional[bool] = None

    gross_pnl: Optional[Decimal] = None
    net_pnl: Optional[Decimal] = None
    gross_pnl_pct: Optional[Decimal] = None
    net_pnl_pct: Optional[Decimal] = None
    duration_hours: Optional[Decimal] = None

    created_at: datetime
    updated_at: Optional[datetime] = None


# ─── Analytics schemas ────────────────────────────────────────────────────────

class AnalyticsSummary(BaseModel):
    total_closed_trades: int
    open_trades: int
    win_rate: Optional[float] = None
    expectancy: Optional[float] = None
    profit_factor: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    avg_duration_hours: Optional[float] = None
    total_net_pnl: float
    total_gross_pnl: float
    rule_compliance_avg: Optional[float] = None
    recent_streak: int = 0          # positive = win streak, negative = loss streak


class EquityCurvePoint(BaseModel):
    date: str
    cumulative_pnl: float
    drawdown_pct: float


class MonthlyPnLPoint(BaseModel):
    year: int
    month: int
    net_pnl: float
    trade_count: int


class BreakdownItem(BaseModel):
    label: str
    count: int
    win_rate: Optional[float] = None
    expectancy: Optional[float] = None
    total_pnl: float = 0.0


class DashboardResponse(BaseModel):
    summary: AnalyticsSummary
    equity_curve: list[EquityCurvePoint]
    monthly_pnl: list[MonthlyPnLPoint]
    by_news_type: list[BreakdownItem]
    by_sector: list[BreakdownItem]
    by_strategy: list[BreakdownItem]
    by_emotional_state: list[BreakdownItem]
    risk_alerts: list[str]


class RiskAlerts(BaseModel):
    alerts: list[str]
    blackout_active: bool
    blackout_hours_remaining: Optional[float] = None


class DailySnapshotCreate(BaseModel):
    date: date
    portfolio_value: Optional[Decimal] = None
    cash_balance: Optional[Decimal] = None
    invested_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl_today: Optional[Decimal] = None
    cumulative_realized_pnl: Optional[Decimal] = None
    num_open_positions: Optional[int] = None
    num_trades_today: Optional[int] = None
    vix_close: Optional[Decimal] = None
    spy_close: Optional[Decimal] = None
    notes: Optional[str] = None


class DailySnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    portfolio_value: Optional[Decimal] = None
    cash_balance: Optional[Decimal] = None
    invested_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl_today: Optional[Decimal] = None
    cumulative_realized_pnl: Optional[Decimal] = None
    num_open_positions: Optional[int] = None
    num_trades_today: Optional[int] = None
    vix_close: Optional[Decimal] = None
    spy_close: Optional[Decimal] = None
    notes: Optional[str] = None
