"""
Score orchestrator — Planet Alignment.

Wraps: fetch fundamentals → call scorer → upsert FactorSnapshot.
This is the ONE place that bridges scorers (pure) to the database.
"""
from __future__ import annotations

import logging
from datetime import date as date_cls
from typing import Callable

from sqlalchemy.orm import Session

from app.models.markets import AlignmentScore, FactorSnapshot
from app.services.factor_scorers import FactorScore
from app.services.factor_scorers.valuation import (
    FACTOR_NAME as VALUATION_NAME,
    score_valuation,
)
from app.services.fundamentals_fetcher import get_fundamentals

log = logging.getLogger(__name__)


# Registry of all available factor scorers.
# Days 4-6 will register additional factors here.
SCORER_REGISTRY: dict[str, Callable[[str, dict], FactorScore]] = {
    VALUATION_NAME: score_valuation,
}


def list_factor_names() -> list[str]:
    """All factor names currently registered."""
    return sorted(SCORER_REGISTRY.keys())


def score_and_persist(
    db: Session,
    ticker: str,
    factor_name: str,
    fundamentals: dict | None = None,
    snapshot_date: date_cls | None = None,
) -> FactorSnapshot:
    """
    Score one factor for one ticker and upsert a FactorSnapshot row.

    If fundamentals is None, fetches them (cached). Otherwise uses what's passed
    — useful for batching so you fetch once and score N factors.

    Returns the persisted FactorSnapshot ORM row.
    """
    ticker = ticker.upper().strip()
    snapshot_date = snapshot_date or date_cls.today()

    scorer = SCORER_REGISTRY.get(factor_name)
    if scorer is None:
        raise ValueError(f"Unknown factor: {factor_name}")

    if fundamentals is None:
        fundamentals = get_fundamentals(ticker)

    result = scorer(ticker, fundamentals)

    existing = (
        db.query(FactorSnapshot)
        .filter(
            FactorSnapshot.ticker == ticker,
            FactorSnapshot.factor_name == factor_name,
            FactorSnapshot.snapshot_date == snapshot_date,
        )
        .first()
    )

    if existing:
        existing.raw_data = result.raw_data
        existing.score = result.score
        existing.verdict = result.verdict
        existing.explanation = result.explanation
        existing.source = result.source
        snapshot = existing
    else:
        snapshot = FactorSnapshot(
            ticker=ticker,
            factor_name=factor_name,
            snapshot_date=snapshot_date,
            raw_data=result.raw_data,
            score=result.score,
            verdict=result.verdict,
            explanation=result.explanation,
            source=result.source,
        )
        db.add(snapshot)

    db.commit()
    db.refresh(snapshot)
    return snapshot


def score_all_factors(
    db: Session,
    ticker: str,
    snapshot_date: date_cls | None = None,
) -> list[FactorSnapshot]:
    """
    Run every registered factor scorer for a single ticker, fetching
    fundamentals once and reusing across scorers.
    """
    ticker = ticker.upper().strip()
    snapshot_date = snapshot_date or date_cls.today()
    fundamentals = get_fundamentals(ticker)

    snapshots = []
    for factor_name in SCORER_REGISTRY:
        try:
            snap = score_and_persist(
                db, ticker, factor_name,
                fundamentals=fundamentals,
                snapshot_date=snapshot_date,
            )
            snapshots.append(snap)
        except Exception as e:
            log.exception("Factor %s failed for %s: %s", factor_name, ticker, e)
    return snapshots


def compute_composite(
    factor_scores: dict[str, int],
    weights: dict[str, float] | None = None,
) -> dict:
    """
    Combine factor scores into a composite alignment score.

    Args:
      factor_scores: e.g. {"valuation": -45, "technical": 20}
                     None values are excluded before computation.
      weights:       optional per-factor weights (must sum to ~1.0).
                     Defaults to equal weights.

    Returns: {composite_score, verdict, bullish_count, bearish_count}
    """
    # Drop factors with missing scores
    clean = {f: s for f, s in factor_scores.items() if s is not None}

    if not clean:
        return {
            "composite_score": None,
            "verdict": "no_trade",
            "bullish_count": 0,
            "bearish_count": 0,
        }

    if weights is None:
        weights = {f: 1.0 / len(clean) for f in clean}
    else:
        # Restrict weights to factors we actually have scores for, then renormalize
        weights = {f: w for f, w in weights.items() if f in clean}
        total = sum(weights.values()) or 1.0
        weights = {f: w / total for f, w in weights.items()}

    composite = sum(clean[f] * weights.get(f, 0) for f in clean)
    composite = int(max(-100, min(100, round(composite))))

    bullish = sum(1 for s in clean.values() if s > 30)
    bearish = sum(1 for s in clean.values() if s < -30)

    if composite > 50 and bullish >= 5:
        verdict = "strong_long"
    elif composite > 20:
        verdict = "long_bias"
    elif composite < -50 and bearish >= 5:
        verdict = "strong_short"
    elif composite < -20:
        verdict = "short_bias"
    else:
        verdict = "no_trade"

    return {
        "composite_score": composite,
        "verdict": verdict,
        "bullish_count": bullish,
        "bearish_count": bearish,
    }


def compute_alignment_score(
    db: Session,
    ticker: str,
    snapshot_date: date_cls | None = None,
    weights: dict[str, float] | None = None,
) -> AlignmentScore:
    """
    Read all FactorSnapshot rows for the day, compute composite, upsert
    AlignmentScore.
    """
    ticker = ticker.upper().strip()
    snapshot_date = snapshot_date or date_cls.today()

    factors = (
        db.query(FactorSnapshot)
        .filter(
            FactorSnapshot.ticker == ticker,
            FactorSnapshot.snapshot_date == snapshot_date,
        )
        .all()
    )

    factor_scores = {f.factor_name: f.score for f in factors}
    composite = compute_composite(factor_scores, weights)

    # Aggregate warnings from all factor raw_data
    warnings: list[str] = []
    for f in factors:
        if isinstance(f.raw_data, dict):
            w = f.raw_data.get("_warnings")
            if isinstance(w, list):
                warnings.extend(w)

    existing = (
        db.query(AlignmentScore)
        .filter(
            AlignmentScore.ticker == ticker,
            AlignmentScore.snapshot_date == snapshot_date,
        )
        .first()
    )

    if existing:
        existing.composite_score = composite["composite_score"]
        existing.verdict = composite["verdict"]
        existing.factor_scores = {f: s for f, s in factor_scores.items() if s is not None}
        existing.warnings = warnings
        score = existing
    else:
        score = AlignmentScore(
            ticker=ticker,
            snapshot_date=snapshot_date,
            composite_score=composite["composite_score"],
            verdict=composite["verdict"],
            factor_scores={f: s for f, s in factor_scores.items() if s is not None},
            warnings=warnings,
        )
        db.add(score)

    db.commit()
    db.refresh(score)
    return score
