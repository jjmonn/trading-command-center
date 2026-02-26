"""
Interactive Brokers connection manager via ib_insync.

Connects to TWS/Gateway on localhost. Fetches positions, account summary,
and market data. Falls back gracefully when IB is not available.

The user must have TWS or IB Gateway running locally.
Port 7497 = paper trading, 7496 = live.
"""
from __future__ import annotations

import logging
from typing import Any

from app.config import settings

log = logging.getLogger(__name__)

# ib_insync is optional — the system must work without it
try:
    from ib_insync import IB, Contract, Option, Stock
    HAS_IB = True
except ImportError:
    HAS_IB = False
    log.warning("ib_insync not installed — IB integration disabled. pip install ib_insync")


class IBConnector:
    """
    Wraps ib_insync for position/account data retrieval.

    All methods return plain dicts/lists so callers never depend on ib_insync types.
    Connection errors are caught and surfaced as status messages.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        client_id: int | None = None,
    ):
        self.host = host or settings.ib_host
        self.port = port or settings.ib_port
        self.client_id = client_id or settings.ib_client_id
        self._ib: Any = None

    @property
    def is_connected(self) -> bool:
        if not HAS_IB or self._ib is None:
            return False
        return self._ib.isConnected()

    def connect(self) -> dict[str, Any]:
        """Attempt to connect. Returns status dict."""
        if not HAS_IB:
            return {"connected": False, "message": "ib_insync not installed"}
        try:
            self._ib = IB()
            self._ib.connect(self.host, self.port, clientId=self.client_id)
            return {
                "connected": True,
                "message": f"Connected to IB at {self.host}:{self.port}",
            }
        except Exception as e:
            log.warning("IB connection failed: %s", e)
            self._ib = None
            return {
                "connected": False,
                "message": f"Connection failed: {e}",
            }

    def disconnect(self) -> None:
        if self._ib and self._ib.isConnected():
            self._ib.disconnect()
        self._ib = None

    def get_status(self) -> dict[str, Any]:
        return {
            "connected": self.is_connected,
            "host": self.host,
            "port": self.port,
            "message": "Connected" if self.is_connected else "Not connected",
        }

    # ─── Account data ────────────────────────────────────────────────────────

    def get_account_summary(self) -> dict[str, str]:
        """Returns account summary tags (NAV, cash, buying power, etc.)."""
        if not self.is_connected:
            return {}
        summary = self._ib.accountSummary()
        return {item.tag: item.value for item in summary}

    def get_account_values(self) -> dict[str, float]:
        """Extract key account values as floats."""
        raw = self.get_account_summary()
        keys = [
            "NetLiquidation", "TotalCashValue", "GrossPositionValue",
            "UnrealizedPnL", "RealizedPnL", "BuyingPower",
            "MaintMarginReq", "AvailableFunds",
        ]
        result: dict[str, float] = {}
        for k in keys:
            if k in raw:
                try:
                    result[k] = float(raw[k])
                except (ValueError, TypeError):
                    pass
        return result

    # ─── Positions ───────────────────────────────────────────────────────────

    def get_positions(self) -> list[dict[str, Any]]:
        """
        Returns all positions as plain dicts.
        Each dict has: ticker, instrument_type, quantity, avg_cost,
        market_price, market_value, unrealized_pnl, realized_pnl,
        currency, ib_con_id, strike, expiry, option_type.
        """
        if not self.is_connected:
            return []

        portfolio_items = self._ib.portfolio()
        positions: list[dict] = []

        for item in portfolio_items:
            contract = item.contract
            pos = {
                "ib_con_id": contract.conId,
                "ticker": contract.symbol,
                "currency": contract.currency,
                "quantity": float(item.position),
                "avg_cost": float(item.averageCost),
                "market_price": float(item.marketPrice),
                "market_value": float(item.marketValue),
                "unrealized_pnl": float(item.unrealizedPNL),
                "realized_pnl": float(item.realizedPNL),
                "strike": None,
                "expiry": None,
                "option_type": None,
                "instrument_type": "stock",
            }

            # Detect instrument type from IB contract
            sec_type = contract.secType
            if sec_type == "OPT":
                pos["instrument_type"] = (
                    "call_option" if contract.right == "C" else "put_option"
                )
                pos["strike"] = float(contract.strike)
                pos["expiry"] = contract.lastTradeDateOrContractMonth
                pos["option_type"] = "CALL" if contract.right == "C" else "PUT"
            elif sec_type == "WAR":
                pos["instrument_type"] = (
                    "call_warrant" if contract.right == "C" else "put_warrant"
                )
                pos["strike"] = float(contract.strike) if contract.strike else None
                pos["expiry"] = contract.lastTradeDateOrContractMonth
            elif sec_type == "FUT":
                pos["instrument_type"] = "stock"  # treat futures as stock-like

            positions.append(pos)

        return positions

    # ─── Market data ─────────────────────────────────────────────────────────

    def get_market_data(self, symbol: str, sec_type: str = "STK") -> dict[str, Any]:
        """Get a snapshot of market data for a symbol."""
        if not self.is_connected:
            return {}

        if sec_type == "STK":
            contract = Stock(symbol, "SMART", "USD")
        else:
            contract = Contract(symbol=symbol, secType=sec_type, exchange="SMART", currency="USD")

        self._ib.qualifyContracts(contract)
        self._ib.reqMktData(contract, snapshot=True)
        self._ib.sleep(2)
        ticker = self._ib.ticker(contract)
        self._ib.cancelMktData(contract)

        return {
            "bid": ticker.bid if ticker.bid != -1 else None,
            "ask": ticker.ask if ticker.ask != -1 else None,
            "last": ticker.last if ticker.last != -1 else None,
            "volume": ticker.volume if ticker.volume != -1 else None,
            "high": ticker.high if ticker.high != -1 else None,
            "low": ticker.low if ticker.low != -1 else None,
        }


# Module-level singleton (lazy)
_connector: IBConnector | None = None


def get_ib_connector() -> IBConnector:
    """Return or create the module-level IB connector singleton."""
    global _connector
    if _connector is None:
        _connector = IBConnector()
    return _connector
