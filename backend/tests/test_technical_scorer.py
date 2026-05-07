"""
Tests for the technical factor scorer.
Uses synthetic OHLCV data — no network calls.
"""
from app.services.factor_scorers import FactorScore
from app.services.factor_scorers.technical import (
    FACTOR_NAME,
    _compute_rsi,
    _compute_sma,
    _compute_volatility_20d,
    score_technical,
)


def _make_prices(
    n: int, start: float = 100.0, daily_return: float = 0.0
) -> list[dict]:
    """Generate N days of synthetic OHLCV data."""
    prices = []
    price = start
    for i in range(n):
        prices.append({
            "date": f"2025-01-{(i % 28) + 1:02d}",
            "open": round(price * 0.999, 2),
            "high": round(price * 1.01, 2),
            "low": round(price * 0.99, 2),
            "close": round(price, 2),
            "volume": 1_000_000,
        })
        price *= (1 + daily_return)
    return prices


def _make_trending_prices(n: int, start: float, end: float) -> list[dict]:
    """Generate prices that move linearly from start to end."""
    step = (end - start) / max(n - 1, 1)
    return [{
        "date": f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
        "open": round(start + step * i, 2),
        "high": round(start + step * i + 1, 2),
        "low": round(start + step * i - 1, 2),
        "close": round(start + step * i, 2),
        "volume": 1_000_000,
    } for i in range(n)]


# ─── RSI computation ────────────────────────────────────────────────────────

class TestComputeRSI:
    def test_all_gains_returns_100(self):
        prices = _make_trending_prices(20, 100, 120)  # monotonic up
        rsi = _compute_rsi(prices)
        assert rsi == 100.0

    def test_all_losses_returns_near_zero(self):
        prices = _make_trending_prices(20, 120, 100)
        rsi = _compute_rsi(prices)
        assert rsi is not None
        assert rsi < 5

    def test_flat_returns_none_or_neutral(self):
        prices = _make_prices(20, 100, 0.0)
        rsi = _compute_rsi(prices)
        # All same close → no gains, no losses → RSI 100 (0 avg loss → RS infinite)
        # OR None depending on implementation
        assert rsi is not None

    def test_insufficient_data(self):
        prices = _make_prices(10, 100, 0.0)  # < 15 needed
        rsi = _compute_rsi(prices)
        assert rsi is None

    def test_mixed_gives_midrange(self):
        # Alternating up/down → RSI near 50
        prices = []
        price = 100
        for i in range(20):
            price = price + (1 if i % 2 == 0 else -1)
            prices.append({"close": price})
        rsi = _compute_rsi(prices)
        assert rsi is not None
        assert 40 < rsi < 60


# ─── SMA computation ────────────────────────────────────────────────────────

class TestComputeSMA:
    def test_sma_flat(self):
        prices = _make_prices(60, 100, 0.0)
        sma = _compute_sma(prices, 50)
        assert sma is not None
        assert abs(sma - 100) < 0.1

    def test_sma_insufficient(self):
        prices = _make_prices(10, 100, 0.0)
        sma = _compute_sma(prices, 50)
        assert sma is None


# ─── Volatility ─────────────────────────────────────────────────────────────

class TestVolatility:
    def test_flat_vol_near_zero(self):
        prices = _make_prices(25, 100, 0.0)
        vol = _compute_volatility_20d(prices)
        assert vol is not None
        assert vol < 1.0

    def test_high_vol(self):
        # Alternating big up/down moves → high variance
        prices = []
        price = 100
        for i in range(25):
            move = 5 if i % 2 == 0 else -5
            price += move
            prices.append({"date": f"2025-01-{i+1:02d}", "close": round(price, 2)})
        vol = _compute_volatility_20d(prices)
        assert vol is not None
        assert vol > 10

    def test_insufficient_data(self):
        prices = _make_prices(15, 100, 0.0)
        vol = _compute_volatility_20d(prices)
        assert vol is None


# ─── Insufficient data ──────────────────────────────────────────────────────

class TestInsufficientData:
    def test_no_prices(self):
        fs = score_technical("X", {})
        assert fs.score is None
        assert "insufficient" in fs.explanation.lower()

    def test_too_few_prices(self):
        fs = score_technical("X", {"_historical_prices": _make_prices(10)})
        assert fs.score is None

    def test_no_current_price_fallback_to_last_close(self):
        prices = _make_prices(30, 100, 0.001)
        fs = score_technical("X", {"_historical_prices": prices})
        assert fs.score is not None
        assert fs.raw_data["current_price"] is not None


# ─── Overbought / overextended (bearish technicals) ────────────────────────

class TestBearishTechnical:
    def test_high_rsi_overbought(self):
        # Monotonic up → RSI 100
        prices = _make_trending_prices(250, 50, 200)
        fs = score_technical("X", {
            "_historical_prices": prices,
            "current_price": 200,
        })
        assert fs.score is not None
        assert fs.score < 0
        assert "overbought" in fs.explanation.lower()

    def test_extended_above_50ma(self):
        # Price 120, 50d MA around 100 → 20% above
        prices = _make_trending_prices(250, 80, 120)
        fs = score_technical("X", {
            "_historical_prices": prices,
            "current_price": 120,
        })
        # Extended from MA should contribute negatively
        assert fs.raw_data.get("dist_from_50ma_pct") is not None

    def test_near_52w_high(self):
        prices = _make_prices(30, 100, 0.001)
        fs = score_technical("X", {
            "_historical_prices": prices,
            "current_price": 100,
            "fifty_two_week_high": 102,
        })
        assert fs.raw_data.get("dist_from_52w_high_pct") is not None


# ─── Oversold / pullback (bullish technicals) ──────────────────────────────

class TestBullishTechnical:
    def test_oversold_rsi(self):
        # Monotonic down → RSI near 0
        prices = _make_trending_prices(250, 200, 80)
        fs = score_technical("X", {
            "_historical_prices": prices,
            "current_price": 80,
        })
        # RSI < 20 → -15 (falling knife), not bullish
        # RSI 20-30 → +15 (oversold bounce)
        assert fs.score is not None

    def test_near_52w_low(self):
        prices = _make_prices(30, 100, -0.001)
        fs = score_technical("X", {
            "_historical_prices": prices,
            "current_price": 50,
            "fifty_two_week_low": 48,
        })
        assert fs.raw_data["dist_from_52w_low_pct"] is not None

    def test_above_200ma_bullish(self):
        # 250 days trending up → above 200MA
        prices = _make_trending_prices(250, 80, 120)
        fs = score_technical("X", {
            "_historical_prices": prices,
            "current_price": 120,
        })
        assert fs.raw_data.get("sma_200") is not None
        if fs.raw_data["sma_200"]:
            assert fs.raw_data["current_price"] > fs.raw_data["sma_200"]


# ─── Neutral ────────────────────────────────────────────────────────────────

class TestNeutralTechnical:
    def test_flat_prices(self):
        prices = _make_prices(250, 100, 0.0)
        fs = score_technical("X", {
            "_historical_prices": prices,
            "current_price": 100,
            "fifty_two_week_high": 120,
            "fifty_two_week_low": 80,
        })
        assert fs.score is not None
        assert fs.verdict in ("neutral", "bull", "bear")


# ─── Output shape ───────────────────────────────────────────────────────────

class TestOutputShape:
    def test_factor_name(self):
        assert FACTOR_NAME == "technical"

    def test_returns_factor_score_type(self):
        prices = _make_prices(30, 100, 0.001)
        fs = score_technical("X", {"_historical_prices": prices})
        assert isinstance(fs, FactorScore)
        assert fs.factor_name == "technical"
        assert fs.source == "yfinance"

    def test_raw_data_keys(self):
        prices = _make_prices(250, 100, 0.001)
        fs = score_technical("X", {
            "_historical_prices": prices,
            "current_price": 128,
            "fifty_two_week_high": 140,
            "fifty_two_week_low": 80,
        })
        assert "rsi_14" in fs.raw_data
        assert "sma_50" in fs.raw_data
        assert "sma_200" in fs.raw_data
        assert "volatility_20d_ann_pct" in fs.raw_data
        assert "fifty_two_week_high" in fs.raw_data

    def test_explanation_under_100_chars(self):
        prices = _make_trending_prices(250, 50, 200)
        fs = score_technical("X", {
            "_historical_prices": prices,
            "current_price": 200,
            "fifty_two_week_high": 205,
            "fifty_two_week_low": 50,
        })
        assert len(fs.explanation) <= 100

    def test_never_raises_on_bad_data(self):
        fs = score_technical("X", {
            "_historical_prices": [{"close": 0}] * 30,
            "current_price": 0,
        })
        assert isinstance(fs, FactorScore)
