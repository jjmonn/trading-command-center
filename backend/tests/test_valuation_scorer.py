"""
Tests for the valuation factor scorer.
Synthetic fundamentals data — no network calls needed.
"""
from app.services.factor_scorers import (
    BEAR_THRESHOLD,
    BULL_THRESHOLD,
    FactorScore,
    clamp,
    derive_verdict,
    insufficient_data,
)
from app.services.factor_scorers.valuation import FACTOR_NAME, score_valuation


# ─── FactorScore primitives ─────────────────────────────────────────────────

class TestPrimitives:
    def test_clamp_within_bounds(self):
        assert clamp(50) == 50

    def test_clamp_above_max(self):
        assert clamp(150) == 100

    def test_clamp_below_min(self):
        assert clamp(-150) == -100

    def test_clamp_rounds(self):
        assert clamp(33.7) == 34

    def test_derive_verdict_bull(self):
        assert derive_verdict(50) == "bull"

    def test_derive_verdict_bear(self):
        assert derive_verdict(-50) == "bear"

    def test_derive_verdict_neutral(self):
        assert derive_verdict(0) == "neutral"

    def test_derive_verdict_at_thresholds(self):
        # Exactly +30 / -30 is NOT bull/bear (strict greater/less)
        assert derive_verdict(30) == "neutral"
        assert derive_verdict(-30) == "neutral"
        assert derive_verdict(31) == "bull"
        assert derive_verdict(-31) == "bear"

    def test_derive_verdict_none(self):
        assert derive_verdict(None) == "neutral"

    def test_insufficient_data_shape(self):
        fs = insufficient_data("foo", "missing P/E")
        assert fs.factor_name == "foo"
        assert fs.score is None
        assert fs.verdict == "neutral"
        assert "missing" in fs.explanation


# ─── score_valuation: insufficient data ─────────────────────────────────────

class TestInsufficientData:
    def test_completely_empty(self):
        fs = score_valuation("XYZ", {})
        assert fs.score is None
        assert fs.verdict == "neutral"

    def test_no_valuation_metrics(self):
        fs = score_valuation("XYZ", {"sector": "Technology", "market_cap": 1e9})
        assert fs.score is None

    def test_only_pe_trailing_works(self):
        # Even one metric is enough
        fs = score_valuation("XYZ", {"pe_trailing": 25})
        assert fs.score is not None


# ─── Overvaluation cases (bear) ─────────────────────────────────────────────

class TestOvervaluation:
    def test_extreme_overvaluation_pe(self):
        # P/E 50 vs sector 20 = 2.5x → -30, plus high PEG → -45 → bear
        fs = score_valuation("XYZ", {
            "pe_trailing": 50, "sector_pe_median": 20,
            "peg": 3.0,
        })
        assert fs.score <= -30
        assert fs.verdict == "bear"
        assert "P/E 50x" in fs.explanation

    def test_moderate_overvaluation_pe(self):
        # P/E 32 vs sector 20 = 1.6x → -20
        fs = score_valuation("XYZ", {
            "pe_trailing": 32, "sector_pe_median": 20,
        })
        assert fs.score == -20

    def test_price_above_target(self):
        # Price 130 vs target 100 → -10 to -20
        fs = score_valuation("XYZ", {
            "pe_trailing": 20, "sector_pe_median": 20,  # neutral on PE
            "current_price": 130, "analyst_target_mean": 100,
        })
        assert fs.score < 0
        assert "above analyst target" in fs.explanation

    def test_high_peg(self):
        fs = score_valuation("XYZ", {
            "pe_trailing": 20, "sector_pe_median": 20,
            "peg": 3.0,
        })
        assert fs.score == -15

    def test_combined_overvaluation_clamped(self):
        # Multiple bear signals → still capped at -100
        fs = score_valuation("XYZ", {
            "pe_trailing": 80, "sector_pe_median": 20,  # -30
            "peg": 5.0,                                  # -15
            "current_price": 200, "analyst_target_mean": 100,  # -20
        })
        assert fs.score == -65
        assert fs.verdict == "bear"

    def test_unprofitable_negative_pe(self):
        fs = score_valuation("XYZ", {"pe_trailing": -10, "sector_pe_median": 20})
        assert fs.score < 0
        assert "unprofitable" in fs.explanation.lower()


# ─── Undervaluation cases (bull) ────────────────────────────────────────────

class TestUndervaluation:
    def test_pe_discount_to_sector(self):
        # P/E 12 vs sector 20 = 0.6x → +20 (eps positive)
        fs = score_valuation("XYZ", {
            "pe_trailing": 12, "sector_pe_median": 20, "eps_trailing": 5.0,
        })
        assert fs.score >= 20
        assert "discount to sector" in fs.explanation

    def test_pe_discount_skipped_if_eps_negative(self):
        # Cheap P/E doesn't help if EPS is negative — usually means earnings collapse
        fs = score_valuation("XYZ", {
            "pe_trailing": 12, "sector_pe_median": 20, "eps_trailing": -2.0,
        })
        assert fs.score is not None
        assert fs.score < 20

    def test_price_below_target(self):
        # Price 70 vs target 100 → +20 (>20% below)
        fs = score_valuation("XYZ", {
            "pe_trailing": 20, "sector_pe_median": 20,
            "current_price": 70, "analyst_target_mean": 100,
        })
        assert fs.score >= 20
        assert "below analyst target" in fs.explanation

    def test_low_peg(self):
        fs = score_valuation("XYZ", {
            "pe_trailing": 20, "sector_pe_median": 20,
            "peg": 0.5,
        })
        assert fs.score == 15

    def test_forward_pe_compression(self):
        # Forward P/E meaningfully lower → +10 (earnings ramp)
        fs = score_valuation("XYZ", {
            "pe_trailing": 30, "sector_pe_median": 28,  # neutral on sector compare
            "pe_forward": 18,
        })
        assert fs.score >= 10
        assert "earnings ramp" in fs.explanation

    def test_combined_undervaluation(self):
        fs = score_valuation("XYZ", {
            "pe_trailing": 12, "sector_pe_median": 20, "eps_trailing": 5.0,  # +20
            "peg": 0.8,                                                        # +15
            "current_price": 70, "analyst_target_mean": 100,                  # +20
            "pe_forward": 9,                                                  # +10
        })
        assert fs.score == 65
        assert fs.verdict == "bull"


# ─── Neutral cases ──────────────────────────────────────────────────────────

class TestNeutral:
    def test_in_line_with_sector(self):
        # P/E 20 vs sector 20 = 1.0x → 0
        fs = score_valuation("XYZ", {
            "pe_trailing": 20, "sector_pe_median": 20,
        })
        assert fs.score == 0
        assert fs.verdict == "neutral"

    def test_slightly_premium_no_penalty(self):
        # P/E 22 vs sector 20 = 1.1x → still within ±20%
        fs = score_valuation("XYZ", {
            "pe_trailing": 22, "sector_pe_median": 20,
        })
        assert fs.score == 0


# ─── Output shape & metadata ────────────────────────────────────────────────

class TestOutputShape:
    def test_returns_factor_score(self):
        fs = score_valuation("NVDA", {"pe_trailing": 50, "sector_pe_median": 25})
        assert isinstance(fs, FactorScore)

    def test_factor_name_constant(self):
        assert FACTOR_NAME == "valuation"
        fs = score_valuation("X", {"pe_trailing": 20})
        assert fs.factor_name == "valuation"

    def test_source_is_yfinance(self):
        fs = score_valuation("X", {"pe_trailing": 20})
        assert fs.source == "yfinance"

    def test_raw_data_preserved(self):
        fs = score_valuation("X", {
            "pe_trailing": 50, "sector_pe_median": 20,
            "pb": 10, "peg": 2.5,
        })
        assert fs.raw_data["pe_trailing"] == 50
        assert fs.raw_data["pb"] == 10

    def test_explanation_under_100_chars(self):
        # Even with many components, explanation is truncated
        fs = score_valuation("X", {
            "pe_trailing": 80, "sector_pe_median": 20,
            "pe_forward": 30,
            "pb": 50, "peg": 3.0,
            "current_price": 200, "analyst_target_mean": 100,
            "eps_trailing": 1.5,
        })
        assert len(fs.explanation) <= 100

    def test_never_raises_on_garbage_input(self):
        # Robustness: even malformed input should not raise
        fs = score_valuation("X", {
            "pe_trailing": "not a number",
            "peg": None,
        })
        # Either returns insufficient data, or handles gracefully
        assert isinstance(fs, FactorScore)
