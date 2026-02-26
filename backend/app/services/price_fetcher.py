"""
Multi-source price fetcher.

Priority: IB (if connected) > yfinance (free fallback).
Used to update market_price on manual positions and to get current quotes.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False
    log.warning("yfinance not installed — price fetching disabled")


def get_current_price(ticker: str) -> float | None:
    """
    Fetch the latest price for a ticker using yfinance.
    Returns None on failure.
    """
    if not HAS_YF:
        return None
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        price = getattr(info, "last_price", None)
        if price is None:
            # fallback: try the last close
            price = getattr(info, "previous_close", None)
        return float(price) if price else None
    except Exception as e:
        log.warning("yfinance price fetch failed for %s: %s", ticker, e)
        return None


def get_batch_prices(tickers: list[str]) -> dict[str, float | None]:
    """
    Fetch prices for multiple tickers at once.
    Returns {ticker: price_or_none}.
    """
    if not HAS_YF or not tickers:
        return {t: None for t in tickers}

    result: dict[str, float | None] = {}
    try:
        data = yf.download(
            " ".join(tickers),
            period="1d",
            progress=False,
            threads=True,
        )
        if data.empty:
            return {t: None for t in tickers}

        # yf.download returns multi-level columns for multiple tickers
        if len(tickers) == 1:
            close = data["Close"]
            result[tickers[0]] = float(close.iloc[-1]) if len(close) > 0 else None
        else:
            for t in tickers:
                try:
                    val = data["Close"][t].iloc[-1]
                    result[t] = float(val) if val == val else None  # NaN check
                except (KeyError, IndexError):
                    result[t] = None
    except Exception as e:
        log.warning("Batch price fetch failed: %s", e)
        result = {t: None for t in tickers}

    # Fill any missing
    for t in tickers:
        if t not in result:
            result[t] = None

    return result


def get_historical_prices(
    ticker: str, period: str = "6mo", interval: str = "1d"
) -> list[dict[str, Any]]:
    """
    Fetch historical OHLCV data.
    Returns list of {date, open, high, low, close, volume}.
    """
    if not HAS_YF:
        return []
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)
        if df.empty:
            return []
        records = []
        for idx, row in df.iterrows():
            records.append({
                "date": idx.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })
        return records
    except Exception as e:
        log.warning("Historical fetch failed for %s: %s", ticker, e)
        return []
