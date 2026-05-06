"""
Factor scorers — Planet Alignment.

Each scorer is a pure function: (ticker, fundamentals) -> FactorScore.
No DB writes inside scorers — persistence happens in score_orchestrator.

Scorers must NEVER raise. On insufficient data, return a FactorScore with
score=None, verdict="neutral", explanation="insufficient data".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Verdict thresholds
BULL_THRESHOLD = 30
BEAR_THRESHOLD = -30


@dataclass
class FactorScore:
    """The output of a single factor scorer."""
    factor_name: str
    score: int | None              # -100 to +100, or None on insufficient data
    verdict: str                   # "bull" | "bear" | "neutral"
    explanation: str               # one-line human summary, ≤ 100 chars
    raw_data: dict[str, Any] = field(default_factory=dict)
    source: str = "yfinance"
    warnings: list[str] = field(default_factory=list)


def clamp(value: float, lo: int = -100, hi: int = 100) -> int:
    """Clamp a score to [-100, +100] and round to int."""
    return int(max(lo, min(hi, round(value))))


def derive_verdict(score: int | None) -> str:
    """Map a numeric score to a verdict label."""
    if score is None:
        return "neutral"
    if score > BULL_THRESHOLD:
        return "bull"
    if score < BEAR_THRESHOLD:
        return "bear"
    return "neutral"


def insufficient_data(factor_name: str, reason: str = "insufficient data") -> FactorScore:
    """Standard return value when a scorer can't produce a real score."""
    return FactorScore(
        factor_name=factor_name,
        score=None,
        verdict="neutral",
        explanation=reason[:100],
        raw_data={},
    )
