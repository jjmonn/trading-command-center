"""
Tests for the sector_trend factor scorer.
Uses synthetic price history — no network calls.
"""
from app.services.factor_scorers import FactorScore
from app.services.factor_scorers.sector_trend import (
    FACTOR_NAME,
    _compute_return,
    score_sector_trend,
)


def _make_prices(n: int, start: float = 100.0, daily_return: float = 0.0) -> list[dict]:
    """Generate N days of synthetic price data with a fixed daily return."""
    prices = []
    price = start
    for i in range(n):
        prices.append({"date": f"2025-01-{i+1:02d}", "close": round(price, 2)})
        price *= (1 + daily_return)
    return prices


# ─── _compute_return ────────────────────────────────────────────────────────

class TestComputeReturn:
    def test_flat_returns_zero(self):
        prices = _make_prices(30, 100, 0.0)
        ret = _compute_return(prices, 1)
        assert ret is not None
        assert abs(ret) < 0.001

    def test_positive_return(self):
        # 21 trading days, ~1% daily → ~23% monthly
        prices = _make_prices(30, 100, 0.01)
        ret = _compute_return(prices, 1)
        assert ret is not None
        assert ret > 0.15

    def test_negative_return(self):
        prices = _make_prices(30, 100, -0.01)
        ret = _compute_return(prices, 1)
        assert ret is not None
        assert ret < -0.15

    def test_insufficient_data(self):
        prices = _make_prices(3, 100, 0.0)
        ret = _compute_return(prices, 1)
        assert ret is None

    def test_empty_prices(self):
        assert _compute_return([], 1) is None


# ─── Insufficient data ──────────────────────────────────────────────────────

class TestInsufficientData:
    def test_no_sector(self):
        fs = score_sector_trend("X", {})
        assert fs.score is None
        assert "no sector" in fs.explanation.lower()

    def test_unknown_sector(self):
        fs = score_sector_trend("X", {"sector": "Alien Technology"})
        assert fs.score is None
        assert "no ETF mapping" in fs.explanation

    def test_no_price_history(self):
        fs = score_sector_trend("X", {
            "sector": "Technology",
            "_sector_etf_prices": [],
            "_spy_prices": [],
        })
        assert fs.score is None


# ─── Sector outperforming SPY (bull) ────────────────────────────────────────

class TestBullishSector:
    def test_sector_strongly_outperforming(self):
        # Sector ETF up 10%, SPY up 2% over 3M
        etf_prices = _make_prices(70, 100, 0.0015)  # ~10% over 63 days
        spy_prices = _make_prices(70, 100, 0.0003)   # ~2% over 63 days
        fs = score_sector_trend("NVDA", {
            "sector": "Technology",
            "_sector_etf_prices": etf_prices,
            "_spy_prices": spy_prices,
        })
        assert fs.score is not None
        assert fs.score > 0
        assert "vs SPY" in fs.explanation

    def test_sector_uptrend_1m(self):
        etf_prices = _make_prices(30, 100, 0.003)  # ~6.5% in 21 days
        spy_prices = _make_prices(30, 100, 0.003)   # same (no relative strength)
        fs = score_sector_trend("NVDA", {
            "sector": "Technology",
            "_sector_etf_prices": etf_prices,
            "_spy_prices": spy_prices,
        })
        assert fs.score is not None
        assert fs.score > 0
        assert "up" in fs.explanation.lower()


class TestBearishSector:
    def test_sector_underperforming(self):
        # Sector ETF down, SPY up
        etf_prices = _make_prices(70, 100, -0.001)
        spy_prices = _make_prices(70, 100, 0.001)
        fs = score_sector_trend("JPM", {
            "sector": "Financial Services",
            "_sector_etf_prices": etf_prices,
            "_spy_prices": spy_prices,
        })
        assert fs.score is not None
        assert fs.score < 0

    def test_sector_downtrend_1m(self):
        etf_prices = _make_prices(30, 100, -0.003)  # ~-6% in 21 days
        spy_prices = _make_prices(30, 100, -0.003)
        fs = score_sector_trend("XOM", {
            "sector": "Energy",
            "_sector_etf_prices": etf_prices,
            "_spy_prices": spy_prices,
        })
        assert fs.score < 0
        assert "down" in fs.explanation.lower()


class TestNeutralSector:
    def test_flat_sector_flat_spy(self):
        etf_prices = _make_prices(70, 100, 0.0)
        spy_prices = _make_prices(70, 100, 0.0)
        fs = score_sector_trend("X", {
            "sector": "Technology",
            "_sector_etf_prices": etf_prices,
            "_spy_prices": spy_prices,
        })
        assert fs.score == 0
        assert fs.verdict == "neutral"


# ─── Output shape ───────────────────────────────────────────────────────────

class TestOutputShape:
    def test_factor_name(self):
        assert FACTOR_NAME == "sector_trend"

    def test_returns_factor_score_type(self):
        etf_prices = _make_prices(70, 100, 0.001)
        spy_prices = _make_prices(70, 100, 0.001)
        fs = score_sector_trend("X", {
            "sector": "Technology",
            "_sector_etf_prices": etf_prices,
            "_spy_prices": spy_prices,
        })
        assert isinstance(fs, FactorScore)
        assert fs.factor_name == "sector_trend"
        assert fs.source == "yfinance"

    def test_raw_data_contains_returns(self):
        etf_prices = _make_prices(70, 100, 0.001)
        spy_prices = _make_prices(70, 100, 0.001)
        fs = score_sector_trend("X", {
            "sector": "Technology",
            "_sector_etf_prices": etf_prices,
            "_spy_prices": spy_prices,
        })
        assert "sector_etf" in fs.raw_data
        assert fs.raw_data["sector_etf"] == "XLK"
        assert "etf_return_1m" in fs.raw_data

    def test_explanation_under_100_chars(self):
        etf_prices = _make_prices(150, 100, 0.002)
        spy_prices = _make_prices(150, 100, -0.001)
        fs = score_sector_trend("X", {
            "sector": "Technology",
            "_sector_etf_prices": etf_prices,
            "_spy_prices": spy_prices,
        })
        assert len(fs.explanation) <= 100

    def test_all_sectors_map_correctly(self):
        # Make sure each supported sector produces a real score
        for sector in ["Technology", "Financial Services", "Energy", "Healthcare"]:
            etf_prices = _make_prices(70, 100, 0.001)
            spy_prices = _make_prices(70, 100, 0.001)
            fs = score_sector_trend("X", {
                "sector": sector,
                "_sector_etf_prices": etf_prices,
                "_spy_prices": spy_prices,
            })
            assert fs.score is not None, f"Failed for sector: {sector}"
