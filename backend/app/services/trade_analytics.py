"""
Trade analytics service.
Computes: win_rate, expectancy, profit_factor, Sharpe, max_drawdown,
equity curve, monthly P&L heatmap, dimension breakdowns, risk alerts.

All edge cases handled explicitly (zero trades, no losses, divide-by-zero).
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.trades import DailySnapshot, Trade


# ─── P&L helpers ─────────────────────────────────────────────────────────────

def compute_trade_pnl(
    entry_price: float,
    exit_price: float,
    quantity: int,
    fees_entry: float,
    fees_exit: float,
    instrument_type: str,
) -> dict[str, float]:
    """
    Compute P&L for a closing trade.
    For all instrument types we treat the trade as a long by default.
    Turbo_short positions have an inverted direction.
    """
    direction = -1 if instrument_type in ("turbo_short", "put_option", "put_warrant") else 1
    gross = (exit_price - entry_price) * quantity * direction
    net = gross - float(fees_entry or 0) - float(fees_exit or 0)
    cost_basis = entry_price * quantity
    gross_pct = (gross / cost_basis * 100) if cost_basis else 0.0
    net_pct = (net / cost_basis * 100) if cost_basis else 0.0

    return {
        "gross_pnl": round(gross, 2),
        "net_pnl": round(net, 2),
        "gross_pnl_pct": round(gross_pct, 4),
        "net_pnl_pct": round(net_pct, 4),
    }


# ─── Aggregate metrics ────────────────────────────────────────────────────────

def get_analytics_summary(db: Session) -> dict[str, Any]:
    """Return all aggregate performance metrics."""
    closed = (
        db.query(Trade)
        .filter(Trade.status == "closed", Trade.net_pnl.isnot(None))
        .all()
    )
    open_count = db.query(Trade).filter(Trade.status == "open").count()

    if not closed:
        return _empty_summary(open_count)

    pnls = [float(t.net_pnl) for t in closed]
    total_net = sum(pnls)
    total_gross = sum(float(t.gross_pnl or 0) for t in closed)

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    win_rate = len(wins) / len(pnls) if pnls else None
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
    loss_rate = 1 - (win_rate or 0)

    expectancy = (win_rate * avg_win - loss_rate * avg_loss) if win_rate is not None else None

    profit_factor = (
        (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else (999.0 if wins else 0.0)
    )

    sharpe = _compute_sharpe(closed)
    max_dd = _compute_max_drawdown(closed)

    durations = [float(t.duration_hours) for t in closed if t.duration_hours is not None]
    avg_duration = sum(durations) / len(durations) if durations else None

    compliance_scores = [float(t.rule_compliance_score) for t in closed if t.rule_compliance_score is not None]
    compliance_avg = sum(compliance_scores) / len(compliance_scores) if compliance_scores else None

    streak = _compute_streak(closed)

    return {
        "total_closed_trades": len(closed),
        "open_trades": open_count,
        "win_rate": round(win_rate, 4) if win_rate is not None else None,
        "expectancy": round(expectancy, 2) if expectancy is not None else None,
        "profit_factor": round(min(profit_factor, 999.0), 2),
        "sharpe_ratio": round(sharpe, 3) if sharpe is not None else None,
        "max_drawdown": round(max_dd, 4) if max_dd is not None else None,
        "avg_duration_hours": round(avg_duration, 1) if avg_duration is not None else None,
        "total_net_pnl": round(total_net, 2),
        "total_gross_pnl": round(total_gross, 2),
        "rule_compliance_avg": round(compliance_avg, 3) if compliance_avg is not None else None,
        "recent_streak": streak,
    }


def _empty_summary(open_count: int) -> dict[str, Any]:
    return {
        "total_closed_trades": 0,
        "open_trades": open_count,
        "win_rate": None,
        "expectancy": None,
        "profit_factor": None,
        "sharpe_ratio": None,
        "max_drawdown": None,
        "avg_duration_hours": None,
        "total_net_pnl": 0.0,
        "total_gross_pnl": 0.0,
        "rule_compliance_avg": None,
        "recent_streak": 0,
    }


def _compute_sharpe(trades: list[Trade]) -> float | None:
    """
    Approximates annualised Sharpe from per-trade returns.
    Uses net_pnl_pct as the return series and assumes ~252 trades/year.
    """
    rets = [float(t.net_pnl_pct) / 100.0 for t in trades if t.net_pnl_pct is not None]
    if len(rets) < 2:
        return None
    mean_r = sum(rets) / len(rets)
    variance = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1)
    std_r = math.sqrt(variance)
    if std_r == 0:
        return None
    # Annualise with sqrt(252) — rough but meaningful for trade-level returns
    risk_free = 0.04 / 252
    return (mean_r - risk_free) / std_r * math.sqrt(252)


def _compute_max_drawdown(trades: list[Trade]) -> float | None:
    """Compute maximum drawdown from cumulative net P&L series."""
    if not trades:
        return None
    sorted_trades = sorted(trades, key=lambda t: t.exit_datetime or datetime.min)
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in sorted_trades:
        cumulative += float(t.net_pnl or 0)
        if cumulative > peak:
            peak = cumulative
        dd = (peak - cumulative) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return max_dd if max_dd > 0 else 0.0


def _compute_streak(trades: list[Trade]) -> int:
    """Return current consecutive win (+n) or loss (-n) streak."""
    if not trades:
        return 0
    sorted_trades = sorted(trades, key=lambda t: t.exit_datetime or datetime.min, reverse=True)
    streak = 0
    sign: int | None = None
    for t in sorted_trades:
        pnl = float(t.net_pnl or 0)
        cur_sign = 1 if pnl > 0 else -1
        if sign is None:
            sign = cur_sign
        if cur_sign == sign:
            streak += cur_sign
        else:
            break
    return streak


# ─── Equity curve ─────────────────────────────────────────────────────────────

def get_equity_curve(db: Session) -> list[dict[str, Any]]:
    """Return sorted cumulative P&L curve with drawdown % at each point."""
    closed = (
        db.query(Trade)
        .filter(Trade.status == "closed", Trade.net_pnl.isnot(None))
        .order_by(Trade.exit_datetime)
        .all()
    )

    points: list[dict] = []
    cumulative = 0.0
    peak = 0.0

    for t in closed:
        cumulative += float(t.net_pnl)
        if cumulative > peak:
            peak = cumulative
        dd = ((peak - cumulative) / peak * 100) if peak > 0 else 0.0
        points.append({
            "date": (t.exit_datetime or t.entry_datetime).strftime("%Y-%m-%d"),
            "cumulative_pnl": round(cumulative, 2),
            "drawdown_pct": round(-dd, 2),
        })

    return points


# ─── Monthly P&L heatmap ──────────────────────────────────────────────────────

def get_monthly_pnl(db: Session) -> list[dict[str, Any]]:
    """Return monthly aggregated P&L for heatmap display."""
    closed = (
        db.query(Trade)
        .filter(Trade.status == "closed", Trade.net_pnl.isnot(None))
        .order_by(Trade.exit_datetime)
        .all()
    )

    buckets: dict[tuple[int, int], dict] = {}
    for t in closed:
        dt = t.exit_datetime or t.entry_datetime
        key = (dt.year, dt.month)
        if key not in buckets:
            buckets[key] = {"year": dt.year, "month": dt.month, "net_pnl": 0.0, "trade_count": 0}
        buckets[key]["net_pnl"] += float(t.net_pnl)
        buckets[key]["trade_count"] += 1

    return [
        {**v, "net_pnl": round(v["net_pnl"], 2)}
        for v in sorted(buckets.values(), key=lambda x: (x["year"], x["month"]))
    ]


# ─── Dimension breakdowns ─────────────────────────────────────────────────────

def _breakdown_by(trades: list[Trade], attr: str) -> list[dict[str, Any]]:
    """Generic breakdown helper."""
    groups: dict[str, list[float]] = defaultdict(list)
    for t in trades:
        key = getattr(t, attr) or "unknown"
        groups[key].append(float(t.net_pnl or 0))

    result = []
    for label, pnls in groups.items():
        wins = [p for p in pnls if p > 0]
        total = sum(pnls)
        wr = len(wins) / len(pnls) if pnls else None
        # simple expectancy per trade in this group
        losses = [p for p in pnls if p <= 0]
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
        exp = ((wr * avg_win) - ((1 - wr) * avg_loss)) if wr is not None else None
        result.append({
            "label": label,
            "count": len(pnls),
            "win_rate": round(wr, 4) if wr is not None else None,
            "expectancy": round(exp, 2) if exp is not None else None,
            "total_pnl": round(total, 2),
        })

    return sorted(result, key=lambda x: x["total_pnl"], reverse=True)


def get_breakdowns(db: Session) -> dict[str, list[dict]]:
    closed = (
        db.query(Trade)
        .filter(Trade.status == "closed", Trade.net_pnl.isnot(None))
        .all()
    )
    return {
        "by_news_type": _breakdown_by(closed, "news_type"),
        "by_sector": _breakdown_by(closed, "sector"),
        "by_strategy": _breakdown_by(closed, "strategy_category"),
        "by_emotional_state": _breakdown_by(closed, "emotional_state_entry"),
    }


# ─── Risk alerts ──────────────────────────────────────────────────────────────

def check_risk_alerts(
    db: Session,
    portfolio_value: float | None = None,
    cash_balance: float | None = None,
) -> dict[str, Any]:
    """
    Check current risk rules and return active alerts.
    Uses latest daily_snapshot for portfolio context if values not provided.
    """
    alerts: list[str] = []
    blackout_active = False
    blackout_hours_remaining: float | None = None

    # Pull latest snapshot for context
    latest_snap = (
        db.query(DailySnapshot)
        .order_by(DailySnapshot.date.desc())
        .first()
    )
    if portfolio_value is None and latest_snap:
        portfolio_value = float(latest_snap.portfolio_value or 0)
    if cash_balance is None and latest_snap:
        cash_balance = float(latest_snap.cash_balance or 0)

    now = datetime.utcnow()

    # 1. Blackout: any loss in last 24 hours
    cutoff_24h = now - timedelta(hours=24)
    recent_loss = (
        db.query(Trade)
        .filter(
            Trade.status == "closed",
            Trade.exit_datetime >= cutoff_24h,
            Trade.net_pnl < 0,
        )
        .order_by(Trade.exit_datetime.desc())
        .first()
    )
    if recent_loss:
        blackout_active = True
        hours_since = (now - recent_loss.exit_datetime).total_seconds() / 3600
        blackout_hours_remaining = max(0.0, 24.0 - hours_since)
        alerts.append(
            f"🔴 24-HOUR BLACKOUT ACTIVE — loss at {recent_loss.exit_datetime.strftime('%H:%M')}. "
            f"{blackout_hours_remaining:.1f}h remaining."
        )

    # 2. Portfolio below €9,000 threshold
    if portfolio_value is not None and portfolio_value < 9000:
        alerts.append(
            f"⚠️ Portfolio €{portfolio_value:,.0f} is below the €9,000 new-position threshold."
        )

    # 3. Cash reserve below 20%
    if portfolio_value and cash_balance is not None:
        cash_pct = (cash_balance / portfolio_value) * 100
        if cash_pct < 20:
            alerts.append(f"⚠️ Cash reserve {cash_pct:.1f}% is below the 20% minimum.")

    # 4. Daily loss > €500
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    daily_pnl = (
        db.query(func.sum(Trade.net_pnl))
        .filter(Trade.status == "closed", Trade.exit_datetime >= today_start)
        .scalar()
    ) or 0
    if float(daily_pnl) < -500:
        alerts.append(f"⚠️ Daily loss €{abs(float(daily_pnl)):,.0f} exceeds €500 limit.")

    # 5. Weekly loss > €1,000
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    weekly_pnl = (
        db.query(func.sum(Trade.net_pnl))
        .filter(Trade.status == "closed", Trade.exit_datetime >= week_start)
        .scalar()
    ) or 0
    if float(weekly_pnl) < -1000:
        alerts.append(f"⚠️ Weekly loss €{abs(float(weekly_pnl)):,.0f} exceeds €1,000 limit.")

    return {
        "alerts": alerts,
        "blackout_active": blackout_active,
        "blackout_hours_remaining": round(blackout_hours_remaining, 1) if blackout_hours_remaining else None,
    }
