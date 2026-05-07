"""
Factor 5: Technical State.

Goal: Is the chart positioned to support entry, or is it overextended?

Inputs (from fundamentals + historical prices):
  - RSI(14) — computed from OHLCV
  - Distance from 50-day and 200-day moving averages
  - Distance from 52-week high / low
  - 20-day price volatility (std dev of daily returns)

Scoring rules:

  RSI(14):
    RSI > 80                   →  -25  (extreme overbought)
    RSI > 70                   →  -15  (overbought)
    RSI < 20                   →  -15  (extreme oversold — caution, falling knife)
    RSI 20-30                  →  +15  (oversold, potential bounce)
    RSI 45-60                  →  +10  (healthy trend range)

  Distance from 50-day MA:
    > +15% above               →  -15  (extended)
    > +5% above                →   0   (healthy trend)
    < -15% below               →  -10  (broken trend)
    -5% to -15% below          →  +10  (pullback to support)

  Distance from 200-day MA:
    above 200d MA              →  +10  (long-term uptrend)
    below 200d MA              →  -10  (long-term downtrend)

  52-week position:
    within 5% of 52w high      →   -5  (limited upside risk)
    within 10% of 52w low      →  +10  (near bottom support)

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

log = logging.getLogger(__name__)

FACTOR_NAME = "technical"


def _compute_rsi(prices: list[dict], period: int = 14) -> float | None:
    """Compute RSI from a list of {close} dicts. Needs at least period+1 data points."""
    if len(prices) < period + 1:
        return None
    closes = [p["close"] for p in prices]
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-(period):]
    gains = [d for d in recent if d > 0]
    losses = [-d for d in recent if d < 0]
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _compute_sma(prices: list[dict], period: int) -> float | None:
    """Compute simple moving average of close prices over the last N days."""
    if len(prices) < period:
        return None
    closes = [p["close"] for p in prices[-period:]]
    return sum(closes) / len(closes)


def _compute_volatility_20d(prices: list[dict]) -> float | None:
    """20-day annualized volatility from daily returns."""
    if len(prices) < 21:
        return None
    closes = [p["close"] for p in prices[-21:]]
    returns = [(closes[i] - closes[i - 1]) / closes[i - 1]
               for i in range(1, len(closes)) if closes[i - 1] != 0]
    if len(returns) < 15:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    daily_vol = variance ** 0.5
    return round(daily_vol * (252 ** 0.5) * 100, 2)  # annualized %


def score_technical(ticker: str, fundamentals: dict[str, Any]) -> FactorScore:
    """
    Score the technical state factor for a ticker.

    Expects fundamentals to contain:
      - _historical_prices: list[{date, open, high, low, close, volume}]
      - fifty_two_week_high, fifty_two_week_low (from yfinance .info)
      - current_price
    """
    prices = fundamentals.get("_historical_prices", [])
    current_price = fundamentals.get("current_price")
    high_52w = fundamentals.get("fifty_two_week_high")
    low_52w = fundamentals.get("fifty_two_week_low")

    if len(prices) < 20:
        return insufficient_data(FACTOR_NAME, "insufficient price history for technical analysis")

    if current_price is None and prices:
        current_price = prices[-1].get("close")

    if current_price is None:
        return insufficient_data(FACTOR_NAME, "no current price available")

    rsi = _compute_rsi(prices)
    sma_50 = _compute_sma(prices, 50)
    sma_200 = _compute_sma(prices, 200)
    volatility_20d = _compute_volatility_20d(prices)

    raw: dict[str, Any] = {
        "current_price": current_price,
        "rsi_14": rsi,
        "sma_50": round(sma_50, 2) if sma_50 else None,
        "sma_200": round(sma_200, 2) if sma_200 else None,
        "fifty_two_week_high": high_52w,
        "fifty_two_week_low": low_52w,
        "volatility_20d_ann_pct": volatility_20d,
    }

    score_total = 0
    components: list[str] = []

    # ─── RSI ─────────────────────────────────────────────────────────────────
    if rsi is not None:
        if rsi > 80:
            score_total -= 25
            components.append(f"RSI {rsi:.0f} extreme overbought")
        elif rsi > 70:
            score_total -= 15
            components.append(f"RSI {rsi:.0f} overbought")
        elif rsi < 20:
            score_total -= 15
            components.append(f"RSI {rsi:.0f} extreme oversold (falling knife)")
        elif rsi <= 30:
            score_total += 15
            components.append(f"RSI {rsi:.0f} oversold (bounce zone)")
        elif 45 <= rsi <= 60:
            score_total += 10
            components.append(f"RSI {rsi:.0f} healthy trend")

    # ─── Distance from 50-day MA ─────────────────────────────────────────────
    if sma_50 and sma_50 > 0:
        dist_50 = (current_price - sma_50) / sma_50
        raw["dist_from_50ma_pct"] = round(dist_50 * 100, 2)
        if dist_50 > 0.15:
            score_total -= 15
            components.append(f"{dist_50*100:.0f}% above 50d MA (extended)")
        elif dist_50 < -0.15:
            score_total -= 10
            components.append(f"{abs(dist_50)*100:.0f}% below 50d MA (broken trend)")
        elif -0.15 <= dist_50 <= -0.05:
            score_total += 10
            components.append(f"{abs(dist_50)*100:.0f}% below 50d MA (pullback)")

    # ─── Distance from 200-day MA ────────────────────────────────────────────
    if sma_200 and sma_200 > 0:
        dist_200 = (current_price - sma_200) / sma_200
        raw["dist_from_200ma_pct"] = round(dist_200 * 100, 2)
        if dist_200 > 0:
            score_total += 10
            components.append("above 200d MA (uptrend)")
        else:
            score_total -= 10
            components.append("below 200d MA (downtrend)")

    # ─── 52-week position ────────────────────────────────────────────────────
    if high_52w and high_52w > 0:
        dist_high = (current_price - high_52w) / high_52w
        raw["dist_from_52w_high_pct"] = round(dist_high * 100, 2)
        if dist_high > -0.05:
            score_total -= 5
            components.append("near 52w high")

    if low_52w and low_52w > 0:
        dist_low = (current_price - low_52w) / low_52w
        raw["dist_from_52w_low_pct"] = round(dist_low * 100, 2)
        if dist_low < 0.10:
            score_total += 10
            components.append("near 52w low (support)")

    final_score = clamp(score_total)
    verdict = derive_verdict(final_score)

    explanation = "; ".join(components[:3]) if components else "technical state inconclusive"
    explanation = explanation[:100]

    return FactorScore(
        factor_name=FACTOR_NAME,
        score=final_score,
        verdict=verdict,
        explanation=explanation,
        raw_data=raw,
        source="yfinance",
    )
