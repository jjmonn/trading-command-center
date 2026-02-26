"""
Tests for trade analytics: P&L computation, aggregate metrics, edge cases.
Covers: zero trades, all wins, all losses, single trade, divide-by-zero.
"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models.trades import Trade
from app.services.trade_analytics import (
    check_risk_alerts,
    compute_trade_pnl,
    get_analytics_summary,
    get_breakdowns,
    get_equity_curve,
    get_monthly_pnl,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_trade(
    db,
    entry_price: float = 10.0,
    exit_price: float = 12.0,
    quantity: int = 10,
    instrument_type: str = "call_option",
    status: str = "closed",
    fees_entry: float = 1.0,
    fees_exit: float = 1.0,
    sector: str = "Technology",
    news_type: str = "earnings",
    strategy_category: str = "momentum_news",
    emotional_state_entry: str = "calm",
    rule_compliance_score: float = 0.9,
    entry_datetime: datetime | None = None,
    exit_datetime: datetime | None = None,
) -> Trade:
    now = datetime.utcnow()
    entry_dt = entry_datetime or now - timedelta(hours=5)
    exit_dt = exit_datetime or now

    pnl = compute_trade_pnl(entry_price, exit_price, quantity, fees_entry, fees_exit, instrument_type)
    duration = (exit_dt - entry_dt).total_seconds() / 3600

    trade = Trade(
        ticker="TEST",
        instrument_type=instrument_type,
        entry_price=Decimal(str(entry_price)),
        exit_price=Decimal(str(exit_price)),
        quantity=quantity,
        fees_entry=Decimal(str(fees_entry)),
        fees_exit=Decimal(str(fees_exit)),
        entry_datetime=entry_dt,
        exit_datetime=exit_dt,
        status=status,
        thesis="Test thesis for unit tests.",
        sector=sector,
        news_type=news_type,
        strategy_category=strategy_category,
        emotional_state_entry=emotional_state_entry,
        rule_compliance_score=Decimal(str(rule_compliance_score)),
        gross_pnl=Decimal(str(pnl["gross_pnl"])),
        net_pnl=Decimal(str(pnl["net_pnl"])),
        gross_pnl_pct=Decimal(str(pnl["gross_pnl_pct"])),
        net_pnl_pct=Decimal(str(pnl["net_pnl_pct"])),
        duration_hours=Decimal(str(round(duration, 2))),
    )
    db.add(trade)
    db.commit()
    return trade


# ─── compute_trade_pnl ───────────────────────────────────────────────────────

class TestComputeTradePnl:
    def test_long_call_profit(self):
        result = compute_trade_pnl(10.0, 15.0, 10, 1.0, 1.0, "call_option")
        assert result["gross_pnl"] == 50.0
        assert result["net_pnl"] == 48.0
        assert result["gross_pnl_pct"] == 50.0

    def test_long_call_loss(self):
        result = compute_trade_pnl(10.0, 8.0, 10, 1.0, 1.0, "call_option")
        assert result["gross_pnl"] == -20.0
        assert result["net_pnl"] == -22.0

    def test_put_option_profit(self):
        """Put options: profit when price drops (direction = -1)."""
        result = compute_trade_pnl(10.0, 8.0, 10, 0, 0, "put_option")
        assert result["gross_pnl"] == 20.0  # (8-10)*10*(-1) = +20

    def test_put_option_loss(self):
        result = compute_trade_pnl(10.0, 12.0, 10, 0, 0, "put_option")
        assert result["gross_pnl"] == -20.0

    def test_turbo_short_profit(self):
        result = compute_trade_pnl(5.0, 3.0, 20, 0, 0, "turbo_short")
        assert result["gross_pnl"] == 40.0  # (3-5)*20*(-1) = 40

    def test_stock_long(self):
        result = compute_trade_pnl(100.0, 110.0, 5, 2.0, 2.0, "stock")
        assert result["gross_pnl"] == 50.0
        assert result["net_pnl"] == 46.0

    def test_zero_cost_basis(self):
        """Edge: entry_price=0 should not crash."""
        result = compute_trade_pnl(0.0, 5.0, 10, 0, 0, "stock")
        assert result["gross_pnl"] == 50.0
        assert result["gross_pnl_pct"] == 0.0  # avoid /0

    def test_call_warrant_direction(self):
        result = compute_trade_pnl(2.0, 3.0, 100, 0, 0, "call_warrant")
        assert result["gross_pnl"] == 100.0  # direction = +1

    def test_put_warrant_direction(self):
        result = compute_trade_pnl(2.0, 1.0, 100, 0, 0, "put_warrant")
        assert result["gross_pnl"] == 100.0  # (1-2)*100*(-1) = 100


# ─── aggregate metrics ───────────────────────────────────────────────────────

class TestAnalyticsSummary:
    def test_zero_trades(self, db):
        """Empty database should return null metrics, not crash."""
        result = get_analytics_summary(db)
        assert result["total_closed_trades"] == 0
        assert result["win_rate"] is None
        assert result["expectancy"] is None
        assert result["profit_factor"] is None
        assert result["sharpe_ratio"] is None
        assert result["total_net_pnl"] == 0.0

    def test_single_winning_trade(self, db):
        _make_trade(db, entry_price=10, exit_price=15, quantity=10)
        result = get_analytics_summary(db)
        assert result["total_closed_trades"] == 1
        assert result["win_rate"] == 1.0
        assert result["profit_factor"] == 999.0  # all wins, no losses
        assert result["total_net_pnl"] == 48.0  # (15-10)*10 - 2 fees

    def test_single_losing_trade(self, db):
        _make_trade(db, entry_price=10, exit_price=5, quantity=10)
        result = get_analytics_summary(db)
        assert result["total_closed_trades"] == 1
        assert result["win_rate"] == 0.0
        assert result["profit_factor"] == 0.0  # no wins

    def test_all_winners(self, db):
        for _ in range(5):
            _make_trade(db, entry_price=10, exit_price=12)
        result = get_analytics_summary(db)
        assert result["win_rate"] == 1.0
        assert result["profit_factor"] == 999.0

    def test_all_losers(self, db):
        for _ in range(5):
            _make_trade(db, entry_price=10, exit_price=8)
        result = get_analytics_summary(db)
        assert result["win_rate"] == 0.0
        assert result["expectancy"] is not None
        assert result["expectancy"] < 0

    def test_mixed_trades(self, db):
        """3 wins + 2 losses should compute meaningful metrics."""
        _make_trade(db, entry_price=10, exit_price=15)  # +48
        _make_trade(db, entry_price=10, exit_price=14)  # +38
        _make_trade(db, entry_price=10, exit_price=12)  # +18
        _make_trade(db, entry_price=10, exit_price=7)   # -32
        _make_trade(db, entry_price=10, exit_price=6)   # -42
        result = get_analytics_summary(db)
        assert result["total_closed_trades"] == 5
        assert result["win_rate"] == 0.6
        assert result["profit_factor"] > 1.0  # net positive
        assert result["sharpe_ratio"] is not None

    def test_open_trades_excluded(self, db):
        """Open trades should NOT be included in metrics."""
        _make_trade(db, status="open", entry_price=10, exit_price=15)
        _make_trade(db, entry_price=10, exit_price=12)
        result = get_analytics_summary(db)
        assert result["total_closed_trades"] == 1
        assert result["open_trades"] == 1

    def test_streak_win(self, db):
        now = datetime.utcnow()
        _make_trade(db, entry_price=10, exit_price=12, exit_datetime=now - timedelta(hours=3))
        _make_trade(db, entry_price=10, exit_price=13, exit_datetime=now - timedelta(hours=2))
        _make_trade(db, entry_price=10, exit_price=14, exit_datetime=now - timedelta(hours=1))
        result = get_analytics_summary(db)
        assert result["recent_streak"] == 3

    def test_streak_loss(self, db):
        now = datetime.utcnow()
        _make_trade(db, entry_price=10, exit_price=8, exit_datetime=now - timedelta(hours=2))
        _make_trade(db, entry_price=10, exit_price=7, exit_datetime=now - timedelta(hours=1))
        result = get_analytics_summary(db)
        assert result["recent_streak"] == -2


# ─── equity curve ────────────────────────────────────────────────────────────

class TestEquityCurve:
    def test_empty(self, db):
        assert get_equity_curve(db) == []

    def test_cumulative(self, db):
        now = datetime.utcnow()
        _make_trade(db, entry_price=10, exit_price=12, exit_datetime=now - timedelta(days=2))  # +18 net
        _make_trade(db, entry_price=10, exit_price=8, exit_datetime=now - timedelta(days=1))   # -22 net
        curve = get_equity_curve(db)
        assert len(curve) == 2
        assert curve[0]["cumulative_pnl"] == 18.0
        # Second point: 18 + (-22) = -4
        assert curve[1]["cumulative_pnl"] == -4.0
        assert curve[1]["drawdown_pct"] < 0  # should show drawdown


# ─── monthly P&L ────────────────────────────────────────────────────────────

class TestMonthlyPnl:
    def test_empty(self, db):
        assert get_monthly_pnl(db) == []

    def test_grouping(self, db):
        now = datetime.utcnow()
        _make_trade(db, entry_price=10, exit_price=12, exit_datetime=now)
        _make_trade(db, entry_price=10, exit_price=14, exit_datetime=now)
        monthly = get_monthly_pnl(db)
        assert len(monthly) == 1
        assert monthly[0]["trade_count"] == 2
        assert monthly[0]["year"] == now.year
        assert monthly[0]["month"] == now.month


# ─── breakdowns ──────────────────────────────────────────────────────────────

class TestBreakdowns:
    def test_empty(self, db):
        result = get_breakdowns(db)
        assert result["by_news_type"] == []
        assert result["by_sector"] == []

    def test_grouping(self, db):
        _make_trade(db, sector="Technology", news_type="earnings")
        _make_trade(db, sector="Energy", news_type="geopolitical")
        result = get_breakdowns(db)
        labels = {r["label"] for r in result["by_sector"]}
        assert "Technology" in labels
        assert "Energy" in labels


# ─── risk alerts ─────────────────────────────────────────────────────────────

class TestRiskAlerts:
    def test_no_alerts_clean_state(self, db):
        result = check_risk_alerts(db, portfolio_value=10000, cash_balance=3000)
        assert result["blackout_active"] is False
        assert len(result["alerts"]) == 0

    def test_portfolio_below_threshold(self, db):
        result = check_risk_alerts(db, portfolio_value=8000, cash_balance=2000)
        assert any("9,000" in a for a in result["alerts"])

    def test_cash_below_20pct(self, db):
        result = check_risk_alerts(db, portfolio_value=10000, cash_balance=1000)
        assert any("20%" in a for a in result["alerts"])

    def test_blackout_after_loss(self, db):
        """A loss in the last 24h should trigger blackout."""
        now = datetime.utcnow()
        _make_trade(
            db,
            entry_price=10,
            exit_price=5,
            exit_datetime=now - timedelta(hours=2),
        )
        result = check_risk_alerts(db, portfolio_value=10000, cash_balance=3000)
        assert result["blackout_active"] is True
        assert result["blackout_hours_remaining"] > 0

    def test_no_blackout_after_24h(self, db):
        """A loss more than 24h ago should NOT trigger blackout."""
        now = datetime.utcnow()
        _make_trade(
            db,
            entry_price=10,
            exit_price=5,
            exit_datetime=now - timedelta(hours=25),
        )
        result = check_risk_alerts(db, portfolio_value=10000, cash_balance=3000)
        assert result["blackout_active"] is False


# ─── P&L pct edge cases ─────────────────────────────────────────────────────

class TestPnlPercentage:
    def test_percentage_calculation(self):
        result = compute_trade_pnl(100.0, 150.0, 1, 0, 0, "stock")
        assert result["gross_pnl_pct"] == 50.0
        assert result["net_pnl_pct"] == 50.0

    def test_fees_reduce_net_pct(self):
        result = compute_trade_pnl(100.0, 150.0, 1, 5.0, 5.0, "stock")
        assert result["gross_pnl"] == 50.0
        assert result["net_pnl"] == 40.0
        assert result["net_pnl_pct"] == 40.0
