"""
Factor 1: Valuation.

Goal: Is the stock priced reasonably given its earnings, growth, and peers?

Inputs (from fundamentals_fetcher):
  - pe_trailing, pe_forward
  - pb (price/book)
  - peg
  - sector_pe_median (lookup table)
  - current_price, analyst_target_mean

Scoring rules (all add to a running total, then clamped to [-100, +100]):

  P/E vs sector median:
    > 2x sector median            →  -30
    > 1.5x sector median          →  -20
    < 0.7x sector median (eps>0)  →  +20
    within ±20% of sector median  →   0

  Analyst target gap (current_price vs target_mean):
    price > target_mean            →  -10 to -20 (linear with gap %)
    price < 80% of target_mean     →  +20

  PEG ratio:
    PEG > 2                        →  -15
    PEG < 1 (and > 0)              →  +15

  Forward P/E < trailing P/E       →  +10 (improving earnings)

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

FACTOR_NAME = "valuation"


def score_valuation(ticker: str, fundamentals: dict[str, Any]) -> FactorScore:
    """
    Score the valuation factor for a ticker.

    Pure function — no I/O, no DB writes. Always returns a FactorScore;
    never raises.
    """
    def _num(key: str) -> float | None:
        """Coerce a fundamentals field to float; None if missing or invalid."""
        v = fundamentals.get(key)
        if v is None:
            return None
        try:
            f = float(v)
            return f if f == f else None  # NaN guard
        except (TypeError, ValueError):
            return None

    pe_trailing = _num("pe_trailing")
    pe_forward = _num("pe_forward")
    pb = _num("pb")
    peg = _num("peg")
    sector_pe = _num("sector_pe_median")
    current_price = _num("current_price")
    target_mean = _num("analyst_target_mean")
    eps_trailing = _num("eps_trailing")

    # Need at least one valuation metric
    if not any([pe_trailing, pe_forward, pb, peg]):
        return insufficient_data(FACTOR_NAME, "no valuation metrics available")

    score_total = 0
    components: list[str] = []
    raw = {
        "pe_trailing": pe_trailing,
        "pe_forward": pe_forward,
        "pb": pb,
        "peg": peg,
        "sector_pe_median": sector_pe,
        "current_price": current_price,
        "analyst_target_mean": target_mean,
        "eps_trailing": eps_trailing,
    }

    # ─── P/E vs sector median ────────────────────────────────────────────────
    if pe_trailing and sector_pe and pe_trailing > 0:
        ratio = pe_trailing / sector_pe
        if ratio > 2.0:
            score_total -= 30
            components.append(f"P/E {pe_trailing:.0f}x vs sector {sector_pe}x (>2x)")
        elif ratio > 1.5:
            score_total -= 20
            components.append(f"P/E {pe_trailing:.0f}x vs sector {sector_pe}x (>1.5x)")
        elif ratio < 0.7 and (eps_trailing is None or eps_trailing > 0):
            score_total += 20
            components.append(f"P/E {pe_trailing:.0f}x discount to sector {sector_pe}x")
        # else: within ±20% — no contribution
    elif pe_trailing and pe_trailing < 0:
        # Negative P/E = unprofitable
        score_total -= 15
        components.append("unprofitable (negative P/E)")

    # ─── Analyst target gap ───────────────────────────────────────────────────
    if current_price and target_mean and target_mean > 0:
        gap_pct = (current_price - target_mean) / target_mean
        if gap_pct < -0.20:
            score_total += 20
            components.append(f"price {abs(gap_pct)*100:.0f}% below analyst target")
        elif gap_pct > 0:
            # Linear penalty: 0% gap → -10, 50%+ gap → -20
            penalty = -10 - min(10, int(gap_pct * 20))
            score_total += penalty
            components.append(f"price {gap_pct*100:.0f}% above analyst target")

    # ─── PEG ratio ────────────────────────────────────────────────────────────
    if peg is not None:
        if peg > 2:
            score_total -= 15
            components.append(f"PEG {peg:.1f} (>2)")
        elif 0 < peg < 1:
            score_total += 15
            components.append(f"PEG {peg:.1f} (<1)")

    # ─── Forward vs trailing P/E (improving earnings signal) ─────────────────
    if pe_trailing and pe_forward and pe_trailing > 0 and pe_forward > 0:
        if pe_forward < pe_trailing * 0.8:
            score_total += 10
            components.append("forward P/E meaningfully lower (earnings ramp)")

    final_score = clamp(score_total)
    verdict = derive_verdict(final_score)

    if not components:
        explanation = f"P/E and peer data inconclusive (score {final_score})"
    else:
        explanation = "; ".join(components[:3])
    explanation = explanation[:100]

    return FactorScore(
        factor_name=FACTOR_NAME,
        score=final_score,
        verdict=verdict,
        explanation=explanation,
        raw_data=raw,
        source="yfinance",
    )
