"""
Tests for fundamentals_fetcher: data extraction, caching, error handling.
Uses mocked yfinance responses — no network calls.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pandas as pd
import pytest

from app.services.fundamentals_fetcher import (
    CACHE_TTL_SECONDS,
    SECTOR_ETF_MAP,
    SECTOR_PE_MEDIANS,
    _to_float,
    _to_int,
    get_fundamentals,
    get_fundamentals_batch,
)


# ─── Fixtures: mock yfinance Ticker objects ─────────────────────────────────

def _make_mock_ticker(info: dict, earnings_history=None, recommendations=None, calendar=None):
    mock = MagicMock()
    mock.info = info
    mock.earnings_history = earnings_history
    mock.recommendations = recommendations
    mock.calendar = calendar
    return mock


NVDA_INFO = {
    "sector": "Technology",
    "industry": "Semiconductors",
    "marketCap": 2_800_000_000_000,
    "currency": "USD",
    "trailingPE": 65.0,
    "forwardPE": 38.0,
    "priceToBook": 52.0,
    "pegRatio": 1.2,
    "priceToSalesTrailing12Months": 30.0,
    "enterpriseToEbitda": 55.0,
    "currentPrice": 950.0,
    "previousClose": 945.0,
    "fiftyTwoWeekHigh": 1000.0,
    "fiftyTwoWeekLow": 400.0,
    "fiftyDayAverage": 900.0,
    "twoHundredDayAverage": 750.0,
    "revenueGrowth": 1.22,
    "earningsGrowth": 5.68,
    "trailingEps": 14.5,
    "earningsQuarterlyGrowth": 7.69,
    "debtToEquity": 41.0,
    "currentRatio": 4.17,
    "totalDebt": 11_000_000_000,
    "totalCash": 31_000_000_000,
    "freeCashflow": 60_000_000_000,
    "operatingCashflow": 64_000_000_000,
    "returnOnEquity": 1.15,
    "targetMeanPrice": 1050.0,
    "targetLowPrice": 800.0,
    "targetHighPrice": 1400.0,
    "numberOfAnalystOpinions": 45,
    "recommendationMean": 1.8,
    "recommendationKey": "buy",
    "dividendYield": 0.0003,
    "exDividendDate": 1717027200,
    "shortRatio": 1.5,
    "shortPercentOfFloat": 0.012,
}

GOOG_INFO = {
    "sector": "Communication Services",
    "industry": "Internet Content & Information",
    "marketCap": 2_100_000_000_000,
    "currency": "USD",
    "trailingPE": 25.0,
    "forwardPE": 20.0,
    "priceToBook": 7.5,
    "pegRatio": 1.0,
    "currentPrice": 170.0,
    "previousClose": 168.0,
    "fiftyTwoWeekHigh": 195.0,
    "fiftyTwoWeekLow": 120.0,
    "debtToEquity": 10.0,
    "currentRatio": 2.1,
    "targetMeanPrice": 200.0,
    "numberOfAnalystOpinions": 55,
    "recommendationMean": 1.6,
    "recommendationKey": "buy",
}

TSLA_INFO = {
    "sector": "Consumer Cyclical",
    "industry": "Auto Manufacturers",
    "marketCap": 800_000_000_000,
    "currency": "USD",
    "trailingPE": 70.0,
    "forwardPE": 55.0,
    "priceToBook": 15.0,
    "pegRatio": 3.5,
    "currentPrice": 250.0,
    "fiftyTwoWeekHigh": 300.0,
    "fiftyTwoWeekLow": 140.0,
    "debtToEquity": 18.0,
    "currentRatio": 1.5,
    "shortRatio": 2.5,
    "shortPercentOfFloat": 0.03,
    "targetMeanPrice": 220.0,
    "numberOfAnalystOpinions": 40,
    "recommendationMean": 3.0,
    "recommendationKey": "hold",
}


# ─── Unit tests: helpers ─────────────────────────────────────────────────────

class TestHelpers:
    def test_to_float_normal(self):
        assert _to_float(42.5) == 42.5

    def test_to_float_int(self):
        assert _to_float(42) == 42.0

    def test_to_float_string(self):
        assert _to_float("3.14") == 3.14

    def test_to_float_none(self):
        assert _to_float(None) is None

    def test_to_float_nan(self):
        assert _to_float(float("nan")) is None

    def test_to_float_bad_string(self):
        assert _to_float("not_a_number") is None

    def test_to_int_normal(self):
        assert _to_int(42) == 42

    def test_to_int_float(self):
        assert _to_int(42.9) == 42

    def test_to_int_none(self):
        assert _to_int(None) is None


# ─── Integration tests: get_fundamentals with mocked yfinance ────────────────

class TestGetFundamentals:
    @patch("app.services.fundamentals_fetcher.yf")
    def test_nvda_full_data(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker(NVDA_INFO)
        result = get_fundamentals("NVDA", skip_cache=True)

        assert result["ticker"] == "NVDA"
        assert result["sector"] == "Technology"
        assert result["industry"] == "Semiconductors"
        assert result["market_cap"] == 2_800_000_000_000
        assert result["pe_trailing"] == 65.0
        assert result["pe_forward"] == 38.0
        assert result["pb"] == 52.0
        assert result["peg"] == 1.2
        assert result["current_price"] == 950.0
        assert result["fifty_two_week_high"] == 1000.0
        assert result["debt_to_equity"] == 41.0
        assert result["free_cash_flow"] == 60_000_000_000
        assert result["analyst_target_mean"] == 1050.0
        assert result["analyst_count"] == 45
        assert result["recommendation_key"] == "buy"
        assert result["short_ratio"] == 1.5
        assert result["sector_pe_median"] == 28

    @patch("app.services.fundamentals_fetcher.yf")
    def test_goog_partial_data(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker(GOOG_INFO)
        result = get_fundamentals("GOOG", skip_cache=True)

        assert result["ticker"] == "GOOG"
        assert result["sector"] == "Communication Services"
        assert result["pe_trailing"] == 25.0
        assert result["sector_pe_median"] == 20
        # Fields not in GOOG_INFO should be None
        assert result["free_cash_flow"] is None
        assert result["ev_ebitda"] is None
        assert result["dividend_yield"] is None

    @patch("app.services.fundamentals_fetcher.yf")
    def test_tsla_with_high_short_interest(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker(TSLA_INFO)
        result = get_fundamentals("TSLA", skip_cache=True)

        assert result["short_pct_of_float"] == 0.03
        assert result["short_ratio"] == 2.5
        assert result["peg"] == 3.5
        assert result["recommendation_key"] == "hold"

    @patch("app.services.fundamentals_fetcher.yf")
    def test_ticker_uppercased(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker({"sector": "Tech"})
        result = get_fundamentals("nvda", skip_cache=True)
        assert result["ticker"] == "NVDA"

    @patch("app.services.fundamentals_fetcher.yf")
    def test_empty_info(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker({})
        result = get_fundamentals("XYZ", skip_cache=True)

        assert result["ticker"] == "XYZ"
        assert result["sector"] is None
        assert result["pe_trailing"] is None
        assert result["current_price"] is None
        assert result["sector_pe_median"] is None

    @patch("app.services.fundamentals_fetcher.yf")
    def test_yfinance_exception(self, mock_yf):
        mock_yf.Ticker.side_effect = Exception("Network error")
        result = get_fundamentals("FAIL", skip_cache=True)
        assert result["ticker"] == "FAIL"
        assert "error" in result

    @patch("app.services.fundamentals_fetcher.yf")
    def test_none_info(self, mock_yf):
        mock_ticker = MagicMock()
        mock_ticker.info = None
        mock_yf.Ticker.return_value = mock_ticker
        result = get_fundamentals("NULL", skip_cache=True)
        assert result["ticker"] == "NULL"
        assert result["sector"] is None

    @patch("app.services.fundamentals_fetcher.yf")
    def test_fallback_to_regular_market_price(self, mock_yf):
        info = {"regularMarketPrice": 123.45}
        mock_yf.Ticker.return_value = _make_mock_ticker(info)
        result = get_fundamentals("TEST", skip_cache=True)
        assert result["current_price"] == 123.45


class TestEarningsHistory:
    @patch("app.services.fundamentals_fetcher.yf")
    def test_earnings_history_parsed(self, mock_yf):
        eh_df = pd.DataFrame({
            "epsEstimate": [1.50, 1.60, 1.70, 1.80],
            "epsActual": [1.55, 1.58, 1.85, 1.95],
            "surprisePercent": [3.3, -1.25, 8.8, 8.3],
        }, index=pd.to_datetime(["2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01"]))

        mock_yf.Ticker.return_value = _make_mock_ticker(
            NVDA_INFO, earnings_history=eh_df,
        )
        result = get_fundamentals("NVDA", skip_cache=True)

        assert len(result["earnings_history"]) == 4
        assert result["earnings_history"][0]["eps_estimate"] == 1.50
        assert result["earnings_history"][0]["eps_actual"] == 1.55
        assert result["earnings_history"][2]["surprise_pct"] == 8.8

    @patch("app.services.fundamentals_fetcher.yf")
    def test_earnings_history_none(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker(
            NVDA_INFO, earnings_history=None,
        )
        result = get_fundamentals("NVDA", skip_cache=True)
        assert result["earnings_history"] == []

    @patch("app.services.fundamentals_fetcher.yf")
    def test_earnings_history_empty_df(self, mock_yf):
        empty_df = pd.DataFrame()
        mock_yf.Ticker.return_value = _make_mock_ticker(
            NVDA_INFO, earnings_history=empty_df,
        )
        result = get_fundamentals("NVDA", skip_cache=True)
        assert result["earnings_history"] == []


class TestRecommendations:
    @patch("app.services.fundamentals_fetcher.yf")
    def test_recommendations_parsed(self, mock_yf):
        recs_df = pd.DataFrame({
            "Firm": ["Goldman Sachs", "Morgan Stanley"],
            "To Grade": ["Buy", "Overweight"],
            "From Grade": ["Neutral", "Equal-Weight"],
            "Action": ["upgrade", "upgrade"],
        }, index=pd.to_datetime(["2025-09-01", "2025-09-15"]))

        mock_yf.Ticker.return_value = _make_mock_ticker(
            NVDA_INFO, recommendations=recs_df,
        )
        result = get_fundamentals("NVDA", skip_cache=True)
        assert len(result["recommendations_summary"]) == 2
        assert result["recommendations_summary"][0]["firm"] == "Goldman Sachs"

    @patch("app.services.fundamentals_fetcher.yf")
    def test_recommendations_none(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker(
            NVDA_INFO, recommendations=None,
        )
        result = get_fundamentals("NVDA", skip_cache=True)
        assert result["recommendations_summary"] == []


class TestCalendar:
    @patch("app.services.fundamentals_fetcher.yf")
    def test_calendar_dict(self, mock_yf):
        cal = {"Earnings Date": "2025-11-20", "Ex-Dividend Date": "2025-12-01"}
        mock_yf.Ticker.return_value = _make_mock_ticker(NVDA_INFO, calendar=cal)
        result = get_fundamentals("NVDA", skip_cache=True)
        assert result["calendar"]["Earnings Date"] == "2025-11-20"

    @patch("app.services.fundamentals_fetcher.yf")
    def test_calendar_none(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker(NVDA_INFO, calendar=None)
        result = get_fundamentals("NVDA", skip_cache=True)
        assert result["calendar"] == {}


# ─── Caching tests ───────────────────────────────────────────────────────────

class TestCaching:
    @patch("app.services.fundamentals_fetcher.yf")
    def test_cache_hit_avoids_api_call(self, mock_yf, tmp_path):
        with patch("app.services.fundamentals_fetcher.CACHE_DIR", tmp_path):
            # First call — populates cache
            mock_yf.Ticker.return_value = _make_mock_ticker(NVDA_INFO)
            result1 = get_fundamentals("NVDA")
            assert mock_yf.Ticker.call_count == 1

            # Second call — should use cache
            result2 = get_fundamentals("NVDA")
            assert mock_yf.Ticker.call_count == 1  # Not called again
            assert result2["pe_trailing"] == 65.0

    @patch("app.services.fundamentals_fetcher.yf")
    def test_cache_expired_refetches(self, mock_yf, tmp_path):
        with patch("app.services.fundamentals_fetcher.CACHE_DIR", tmp_path):
            # Write expired cache
            cache_data = {"ticker": "NVDA", "pe_trailing": 50.0, "_cached_at": time.time() - CACHE_TTL_SECONDS - 100}
            cache_file = tmp_path / "NVDA.json"
            cache_file.write_text(json.dumps(cache_data))

            mock_yf.Ticker.return_value = _make_mock_ticker(NVDA_INFO)
            result = get_fundamentals("NVDA")
            assert mock_yf.Ticker.call_count == 1
            assert result["pe_trailing"] == 65.0  # Fresh data, not cached 50.0

    @patch("app.services.fundamentals_fetcher.yf")
    def test_skip_cache_forces_refresh(self, mock_yf, tmp_path):
        with patch("app.services.fundamentals_fetcher.CACHE_DIR", tmp_path):
            mock_yf.Ticker.return_value = _make_mock_ticker(NVDA_INFO)
            get_fundamentals("NVDA")
            get_fundamentals("NVDA", skip_cache=True)
            assert mock_yf.Ticker.call_count == 2

    @patch("app.services.fundamentals_fetcher.yf")
    def test_corrupt_cache_refetches(self, mock_yf, tmp_path):
        with patch("app.services.fundamentals_fetcher.CACHE_DIR", tmp_path):
            cache_file = tmp_path / "NVDA.json"
            cache_file.write_text("not valid json{{{")

            mock_yf.Ticker.return_value = _make_mock_ticker(NVDA_INFO)
            result = get_fundamentals("NVDA")
            assert result["pe_trailing"] == 65.0


# ─── Batch fetch ─────────────────────────────────────────────────────────────

class TestBatchFetch:
    @patch("app.services.fundamentals_fetcher.yf")
    def test_batch_returns_all(self, mock_yf):
        def mock_ticker_factory(ticker):
            lookup = {"NVDA": NVDA_INFO, "GOOG": GOOG_INFO, "TSLA": TSLA_INFO}
            return _make_mock_ticker(lookup.get(ticker, {}))

        mock_yf.Ticker.side_effect = mock_ticker_factory
        results = get_fundamentals_batch(["NVDA", "GOOG", "TSLA"], skip_cache=True)

        assert len(results) == 3
        assert results["NVDA"]["pe_trailing"] == 65.0
        assert results["GOOG"]["pe_trailing"] == 25.0
        assert results["TSLA"]["pe_trailing"] == 70.0


# ─── Sector mapping tests ───────────────────────────────────────────────────

class TestSectorMappings:
    def test_all_major_sectors_have_etf(self):
        required_sectors = [
            "Technology", "Financial Services", "Healthcare",
            "Energy", "Industrials", "Utilities",
        ]
        for sector in required_sectors:
            assert sector in SECTOR_ETF_MAP, f"Missing ETF for {sector}"

    def test_all_major_sectors_have_pe_median(self):
        for sector in SECTOR_ETF_MAP:
            assert sector in SECTOR_PE_MEDIANS, f"Missing PE median for {sector}"

    def test_sector_pe_medians_reasonable(self):
        for sector, pe in SECTOR_PE_MEDIANS.items():
            assert 5 <= pe <= 50, f"PE median {pe} for {sector} seems unreasonable"
