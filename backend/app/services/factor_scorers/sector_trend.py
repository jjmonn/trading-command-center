"""
Factor 4: Sector Trend.

Goal: Is the sector working with you or against you?

Inputs:
  - Ticker's sector (from fundamentals → SECTOR_ETF_MAP)
  - Sector ETF (XLK, XLF, etc.) 1M, 3M, 6M returns
  - SPY same-period returns (sector relative strength)

Scoring rules:

  Relative strength vs SPY (sector ETF return - SPY return):
    3M relative > +5%          →  +20  (sector outperforming)
    3M relative > +2%          →  +10
    3M relative < -5%          →  -20  (sector underperforming)
    3M relative < -2%          →  -10

  Trend direction (sector ETF 1M return):
    1M > +5%                   →  +15  (strong uptrend)
    1M > +2%                   →  +10
    1M < -5%                   →  -15  (strong downtrend)
    1M < -2%                   →  -10

  Momentum (1M vs 3M monthly rate — accelerating or decelerating):
    1M_monthly > 3M_monthly    →  +10  (accelerating)
    1M_monthly < 3M_monthly    →  -10  (decelerating)

  Sum, clamp to [-100, +100].

Verdict thresholds: score < -30 = bear, > +30 = bull, else neutral.
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.factor_scorers import (
    FactorScore,
    clamp,
    derive_verdict,
    insufficient_data,
)
from app.services.fundamentals_fetcher import SECTOR_ETF_MAP

log = logging.getLogger(__name__)

FACTOR_NAME = "sector_trend"


def _compute_return(prices: list[dict], months: int) -> float | None:
    """Compute return over the last N months from a list of {date, close} dicts."""
    if not prices or len(prices) < 2:
        return None
    trading_days = months * 21
    if len(prices) < trading_days:
        if len(prices) < max(5, trading_days // 2):
            return None
        trading_days = len(prices) - 1
    start_price = prices[-(trading_days + 1)]["close"]
    end_price = prices[-1]["close"]
    if not start_price or start_price == 0:
        return None
    return (end_price - start_price) / start_price


def score_sector_trend(ticker: str, fundamentals: dict[str, Any]) -> FactorScore:
    """
    Score the sector trend factor for a ticker.

    Uses pre-fetched historical price data for the sector ETF and SPY.
    Expects fundamentals to contain:
      - sector: str (maps to ETF via SECTOR_ETF_MAP)
      - _sector_etf_prices: list[{date, close}]  (injected by orchestrator)
      - _spy_prices: list[{date, close}]  (injected by orchestrator)
    """
    sector = fundamentals.get("sector")
    if not sector:
        return insufficient_data(FACTOR_NAME, "no sector data available")

    sector_etf = SECTOR_ETF_MAP.get(sector)
    if not sector_etf:
        return insufficient_data(FACTOR_NAME, f"no ETF mapping for sector: {sector}")

    etf_prices = fundamentals.get("_sector_etf_prices", [])
    spy_prices = fundamentals.get("_spy_prices", [])

    if len(etf_prices) < 10 or len(spy_prices) < 10:
        return insufficient_data(FACTOR_NAME, "insufficient price history for sector analysis")

    etf_1m = _compute_return(etf_prices, 1)
    etf_3m = _compute_return(etf_prices, 3)
    etf_6m = _compute_return(etf_prices, 6)
    spy_1m = _compute_return(spy_prices, 1)
    spy_3m = _compute_return(spy_prices, 3)

    raw = {
        "sector": sector,
        "sector_etf": sector_etf,
        "etf_return_1m": _pct(etf_1m),
        "etf_return_3m": _pct(etf_3m),
        "etf_return_6m": _pct(etf_6m),
        "spy_return_1m": _pct(spy_1m),
        "spy_return_3m": _pct(spy_3m),
    }

    score_total = 0
    components: list[str] = []

    # ─── Relative strength vs SPY (3M) ──────────────────────────────────────
    if etf_3m is not None and spy_3m is not None:
        rel_3m = etf_3m - spy_3m
        raw["relative_3m"] = _pct(rel_3m)
        if rel_3m > 0.05:
            score_total += 20
            components.append(f"sector +{rel_3m*100:.1f}% vs SPY (3M)")
        elif rel_3m > 0.02:
            score_total += 10
            components.append(f"sector +{rel_3m*100:.1f}% vs SPY (3M)")
        elif rel_3m < -0.05:
            score_total -= 20
            components.append(f"sector {rel_3m*100:.1f}% vs SPY (3M)")
        elif rel_3m < -0.02:
            score_total -= 10
            components.append(f"sector {rel_3m*100:.1f}% vs SPY (3M)")

    # ─── Sector trend direction (1M) ────────────────────────────────────────
    if etf_1m is not None:
        if etf_1m > 0.05:
            score_total += 15
            components.append(f"sector up {etf_1m*100:.1f}% (1M)")
        elif etf_1m > 0.02:
            score_total += 10
            components.append(f"sector up {etf_1m*100:.1f}% (1M)")
        elif etf_1m < -0.05:
            score_total -= 15
            components.append(f"sector down {etf_1m*100:.1f}% (1M)")
        elif etf_1m < -0.02:
            score_total -= 10
            components.append(f"sector down {etf_1m*100:.1f}% (1M)")

    # ─── Momentum: accelerating vs decelerating ────────────────────────────
    if etf_1m is not None and etf_3m is not None and etf_3m != 0:
        monthly_3m = etf_3m / 3
        if etf_1m > monthly_3m + 0.005:
            score_total += 10
            components.append("momentum accelerating")
        elif etf_1m < monthly_3m - 0.005:
            score_total -= 10
            components.append("momentum decelerating")

    final_score = clamp(score_total)
    verdict = derive_verdict(final_score)

    explanation = "; ".join(components[:3]) if components else f"sector trend neutral ({sector})"
    explanation = explanation[:100]

    return FactorScore(
        factor_name=FACTOR_NAME,
        score=final_score,
        verdict=verdict,
        explanation=explanation,
        raw_data=raw,
        source="yfinance",
    )


def _pct(val: float | None) -> float | None:
    """Round a decimal to a clean percentage for raw_data."""
    if val is None:
        return None
    return round(val * 100, 2)
