"""
Fundamentals data fetcher — pulls valuation, earnings, balance sheet,
analyst, and calendar data from yfinance.

Used by all 8 Planet Alignment factor scorers.
Includes file-based caching with 24h TTL to avoid hammering yfinance.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False
    log.warning("yfinance not installed — fundamentals fetching disabled")

CACHE_DIR = Path(os.environ.get("FUNDAMENTALS_CACHE_DIR", ".cache/fundamentals"))
CACHE_TTL_SECONDS = 24 * 60 * 60

# Sector → ETF mapping for sector trend factor
SECTOR_ETF_MAP = {
    "Technology": "XLK",
    "Communication Services": "XLC",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Financial Services": "XLF",
    "Financials": "XLF",
    "Healthcare": "XLV",
    "Health Care": "XLV",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
}

# Sector median P/E lookup (approximate, updated periodically)
SECTOR_PE_MEDIANS = {
    "Technology": 28,
    "Communication Services": 20,
    "Consumer Cyclical": 22,
    "Consumer Defensive": 24,
    "Energy": 12,
    "Financial Services": 14,
    "Financials": 14,
    "Healthcare": 22,
    "Health Care": 22,
    "Industrials": 20,
    "Basic Materials": 15,
    "Materials": 15,
    "Real Estate": 35,
    "Utilities": 18,
}


def _safe_get(d: dict, key: str, default=None):
    """Get a value from a dict, returning default if key missing or value is None."""
    val = d.get(key)
    return val if val is not None else default


def _cache_path(ticker: str) -> Path:
    return CACHE_DIR / f"{ticker.upper()}.json"


def _read_cache(ticker: str) -> dict | None:
    path = _cache_path(ticker)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data.get("_cached_at", 0) < CACHE_TTL_SECONDS:
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _write_cache(ticker: str, data: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data["_cached_at"] = time.time()
        _cache_path(ticker).write_text(json.dumps(data, default=str))
    except OSError as e:
        log.warning("Cache write failed for %s: %s", ticker, e)


def get_fundamentals(ticker: str, skip_cache: bool = False) -> dict[str, Any]:
    """
    Fetch comprehensive fundamentals for a ticker.

    Returns a dict with keys:
      Identification: ticker, sector, industry, market_cap, currency
      Valuation: pe_trailing, pe_forward, pb, peg, ps, ev_ebitda,
                 pe_5y_avg (if computable), sector_pe_median
      Price context: current_price, fifty_two_week_high, fifty_two_week_low,
                     fifty_day_avg, two_hundred_day_avg
      Earnings: revenue_growth, earnings_growth, eps_trailing,
                earnings_quarterly_growth
      Balance sheet: debt_to_equity, current_ratio, total_debt, total_cash,
                     free_cash_flow, operating_cash_flow, return_on_equity
      Analyst: analyst_target_mean, analyst_target_low, analyst_target_high,
               analyst_count, recommendation_mean, recommendation_key
      Dividends: dividend_yield, ex_dividend_date
      Short interest: short_ratio, short_pct_of_float

    Missing values are None. All numeric values are floats.
    """
    ticker = ticker.upper().strip()

    if not skip_cache:
        cached = _read_cache(ticker)
        if cached:
            log.debug("Cache hit for %s", ticker)
            return cached

    if not HAS_YF:
        return {"ticker": ticker, "error": "yfinance not installed"}

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception as e:
        log.warning("yfinance info fetch failed for %s: %s", ticker, e)
        return {"ticker": ticker, "error": str(e)}

    sector = _safe_get(info, "sector")
    sector_pe = SECTOR_PE_MEDIANS.get(sector) if sector else None

    result: dict[str, Any] = {
        "ticker": ticker,

        # Identification
        "sector": sector,
        "industry": _safe_get(info, "industry"),
        "market_cap": _to_float(_safe_get(info, "marketCap")),
        "currency": _safe_get(info, "currency", "USD"),

        # Valuation
        "pe_trailing": _to_float(_safe_get(info, "trailingPE")),
        "pe_forward": _to_float(_safe_get(info, "forwardPE")),
        "pb": _to_float(_safe_get(info, "priceToBook")),
        "peg": _to_float(_safe_get(info, "pegRatio")),
        "ps": _to_float(_safe_get(info, "priceToSalesTrailing12Months")),
        "ev_ebitda": _to_float(_safe_get(info, "enterpriseToEbitda")),
        "sector_pe_median": sector_pe,

        # Price context
        "current_price": _to_float(
            _safe_get(info, "currentPrice")
            or _safe_get(info, "regularMarketPrice")
        ),
        "previous_close": _to_float(_safe_get(info, "previousClose")),
        "fifty_two_week_high": _to_float(_safe_get(info, "fiftyTwoWeekHigh")),
        "fifty_two_week_low": _to_float(_safe_get(info, "fiftyTwoWeekLow")),
        "fifty_day_avg": _to_float(_safe_get(info, "fiftyDayAverage")),
        "two_hundred_day_avg": _to_float(_safe_get(info, "twoHundredDayAverage")),

        # Earnings / growth
        "revenue_growth": _to_float(_safe_get(info, "revenueGrowth")),
        "earnings_growth": _to_float(_safe_get(info, "earningsGrowth")),
        "eps_trailing": _to_float(_safe_get(info, "trailingEps")),
        "earnings_quarterly_growth": _to_float(
            _safe_get(info, "earningsQuarterlyGrowth")
        ),

        # Balance sheet health
        "debt_to_equity": _to_float(_safe_get(info, "debtToEquity")),
        "current_ratio": _to_float(_safe_get(info, "currentRatio")),
        "total_debt": _to_float(_safe_get(info, "totalDebt")),
        "total_cash": _to_float(_safe_get(info, "totalCash")),
        "free_cash_flow": _to_float(_safe_get(info, "freeCashflow")),
        "operating_cash_flow": _to_float(_safe_get(info, "operatingCashflow")),
        "return_on_equity": _to_float(_safe_get(info, "returnOnEquity")),

        # Analyst
        "analyst_target_mean": _to_float(_safe_get(info, "targetMeanPrice")),
        "analyst_target_low": _to_float(_safe_get(info, "targetLowPrice")),
        "analyst_target_high": _to_float(_safe_get(info, "targetHighPrice")),
        "analyst_count": _to_int(_safe_get(info, "numberOfAnalystOpinions")),
        "recommendation_mean": _to_float(_safe_get(info, "recommendationMean")),
        "recommendation_key": _safe_get(info, "recommendationKey"),

        # Dividends
        "dividend_yield": _to_float(_safe_get(info, "dividendYield")),
        "ex_dividend_date": _safe_get(info, "exDividendDate"),

        # Short interest
        "short_ratio": _to_float(_safe_get(info, "shortRatio")),
        "short_pct_of_float": _to_float(_safe_get(info, "shortPercentOfFloat")),
    }

    # Fetch earnings history for beat/miss tracking
    result["earnings_history"] = _fetch_earnings_history(t)

    # Fetch analyst recommendations summary
    result["recommendations_summary"] = _fetch_recommendations(t)

    # Fetch upcoming calendar events
    result["calendar"] = _fetch_calendar(t)

    _write_cache(ticker, result)
    return result


def get_fundamentals_batch(tickers: list[str], skip_cache: bool = False) -> dict[str, dict]:
    """Fetch fundamentals for multiple tickers. Returns {ticker: fundamentals_dict}."""
    return {t: get_fundamentals(t, skip_cache=skip_cache) for t in tickers}


def _fetch_earnings_history(ticker_obj) -> list[dict]:
    """Extract last 4 quarters of earnings beat/miss data."""
    try:
        eh = ticker_obj.earnings_history
        if eh is None or (hasattr(eh, "empty") and eh.empty):
            return []
        records = []
        for _, row in eh.tail(4).iterrows():
            records.append({
                "quarter": str(getattr(row, "name", "")),
                "eps_estimate": _to_float(row.get("epsEstimate")),
                "eps_actual": _to_float(row.get("epsActual")),
                "surprise_pct": _to_float(row.get("surprisePercent")),
            })
        return records
    except Exception as e:
        log.debug("Earnings history fetch failed: %s", e)
        return []


def _fetch_recommendations(ticker_obj) -> list[dict]:
    """Extract recent analyst recommendations."""
    try:
        recs = ticker_obj.recommendations
        if recs is None or (hasattr(recs, "empty") and recs.empty):
            return []
        recent = recs.tail(10)
        records = []
        for idx, row in recent.iterrows():
            records.append({
                "date": str(idx),
                "firm": row.get("Firm", ""),
                "to_grade": row.get("To Grade", ""),
                "from_grade": row.get("From Grade", ""),
                "action": row.get("Action", ""),
            })
        return records
    except Exception as e:
        log.debug("Recommendations fetch failed: %s", e)
        return []


def _fetch_calendar(ticker_obj) -> dict:
    """Extract upcoming calendar events (earnings date, ex-div date)."""
    try:
        cal = ticker_obj.calendar
        if cal is None:
            return {}
        if isinstance(cal, dict):
            return {k: str(v) for k, v in cal.items() if v is not None}
        return {}
    except Exception as e:
        log.debug("Calendar fetch failed: %s", e)
        return {}


def _to_float(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return f if f == f else None  # NaN check
    except (ValueError, TypeError):
        return None


def _to_int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
