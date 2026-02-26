"""
Tests for Pydantic schema validation: enforces pre-trade planning rules.
"""
import pytest
from pydantic import ValidationError

from app.schemas.trades import TradeCreate


class TestTradeCreateValidation:
    def _base_payload(self, **overrides) -> dict:
        payload = {
            "ticker": "NVDA",
            "instrument_type": "call_option",
            "entry_price": 5.50,
            "quantity": 10,
            "thesis": "Strong AI demand thesis, earnings beat expected.",
            "emotional_state_entry": "calm",
            "profit_target_pct": 25.0,
            "stop_loss_pct": 15.0,
        }
        payload.update(overrides)
        return payload

    def test_valid_trade(self):
        """A fully valid trade should pass."""
        t = TradeCreate(**self._base_payload())
        assert t.ticker == "NVDA"

    def test_ticker_uppercased(self):
        t = TradeCreate(**self._base_payload(ticker="nvda"))
        assert t.ticker == "NVDA"

    def test_ticker_trimmed(self):
        t = TradeCreate(**self._base_payload(ticker="  nvda  "))
        assert t.ticker == "NVDA"

    def test_missing_thesis_fails(self):
        with pytest.raises(ValidationError, match="thesis"):
            TradeCreate(**self._base_payload(thesis=""))

    def test_short_thesis_fails(self):
        with pytest.raises(ValidationError):
            TradeCreate(**self._base_payload(thesis="short"))

    def test_missing_profit_target_fails(self):
        with pytest.raises(ValidationError, match="profit_target"):
            TradeCreate(**self._base_payload(profit_target_pct=None, profit_target_price=None))

    def test_missing_stop_loss_fails(self):
        with pytest.raises(ValidationError, match="stop_loss"):
            TradeCreate(**self._base_payload(stop_loss_pct=None, stop_loss_price=None))

    def test_profit_target_price_alone_ok(self):
        """Having just a price target (no %) is valid."""
        t = TradeCreate(**self._base_payload(profit_target_pct=None, profit_target_price=7.0))
        assert t.profit_target_price == 7.0

    def test_stop_loss_price_alone_ok(self):
        t = TradeCreate(**self._base_payload(stop_loss_pct=None, stop_loss_price=4.0))
        assert t.stop_loss_price == 4.0

    def test_zero_entry_price_fails(self):
        with pytest.raises(ValidationError):
            TradeCreate(**self._base_payload(entry_price=0))

    def test_negative_quantity_fails(self):
        with pytest.raises(ValidationError):
            TradeCreate(**self._base_payload(quantity=-5))

    def test_compliance_score_bounds(self):
        t = TradeCreate(**self._base_payload(rule_compliance_score=0.0))
        assert t.rule_compliance_score == 0.0
        t2 = TradeCreate(**self._base_payload(rule_compliance_score=1.0))
        assert t2.rule_compliance_score == 1.0

    def test_compliance_over_1_fails(self):
        with pytest.raises(ValidationError):
            TradeCreate(**self._base_payload(rule_compliance_score=1.5))
