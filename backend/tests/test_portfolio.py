"""
Tests for portfolio/positions: CRUD, dashboard computation, risk alerts, edge cases.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.portfolio import PortfolioHistory, Position


# ─── Test DB fixture ─────────────────────────────────────────────────────────

@pytest.fixture()
def client():
    """FastAPI test client with an in-memory SQLite database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c, TestSession
    app.dependency_overrides.clear()


# ─── helpers ─────────────────────────────────────────────────────────────────

def _create_position(client_tuple, **overrides) -> dict:
    client, _ = client_tuple
    payload = {
        "ticker": "NVDA",
        "instrument_type": "stock",
        "quantity": 10,
        "avg_cost": 100.0,
        "market_price": 120.0,
        "currency": "USD",
        "sector": "Technology",
    }
    payload.update(overrides)
    res = client.post("/api/v1/portfolio/positions", json=payload)
    assert res.status_code == 201
    return res.json()


# ─── Position CRUD ───────────────────────────────────────────────────────────

class TestPositionCRUD:
    def test_create_position(self, client):
        pos = _create_position(client)
        assert pos["ticker"] == "NVDA"
        assert pos["instrument_type"] == "stock"
        assert float(pos["quantity"]) == 10
        assert pos["source"] == "manual"

    def test_create_position_auto_computes(self, client):
        """market_value and unrealized_pnl should be auto-computed."""
        pos = _create_position(client, avg_cost=100.0, market_price=120.0, quantity=10)
        assert float(pos["market_value"]) == 1200.0
        assert float(pos["unrealized_pnl"]) == 200.0

    def test_list_positions(self, client):
        c, _ = client
        _create_position(client, ticker="NVDA")
        _create_position(client, ticker="AAPL")
        res = c.get("/api/v1/portfolio/positions")
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_get_single_position(self, client):
        c, _ = client
        pos = _create_position(client)
        res = c.get(f"/api/v1/portfolio/positions/{pos['id']}")
        assert res.status_code == 200
        assert res.json()["ticker"] == "NVDA"

    def test_get_nonexistent_returns_404(self, client):
        c, _ = client
        res = c.get("/api/v1/portfolio/positions/999")
        assert res.status_code == 404

    def test_update_position(self, client):
        c, _ = client
        pos = _create_position(client, market_price=100.0, avg_cost=80.0, quantity=10)
        res = c.patch(
            f"/api/v1/portfolio/positions/{pos['id']}",
            json={"market_price": 130.0, "sector": "Semiconductors"},
        )
        assert res.status_code == 200
        updated = res.json()
        assert float(updated["market_price"]) == 130.0
        assert updated["sector"] == "Semiconductors"
        # market_value should be recomputed
        assert float(updated["market_value"]) == 1300.0
        # unrealized_pnl should be recomputed
        assert float(updated["unrealized_pnl"]) == 500.0  # (130-80)*10

    def test_delete_position(self, client):
        c, _ = client
        pos = _create_position(client)
        res = c.delete(f"/api/v1/portfolio/positions/{pos['id']}")
        assert res.status_code == 204
        # Verify gone
        res = c.get(f"/api/v1/portfolio/positions/{pos['id']}")
        assert res.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        c, _ = client
        res = c.delete("/api/v1/portfolio/positions/999")
        assert res.status_code == 404

    def test_ticker_uppercased(self, client):
        pos = _create_position(client, ticker="nvda")
        assert pos["ticker"] == "NVDA"

    def test_inactive_positions_excluded_by_default(self, client):
        c, _ = client
        pos = _create_position(client)
        c.patch(f"/api/v1/portfolio/positions/{pos['id']}", json={"is_active": False})
        res = c.get("/api/v1/portfolio/positions")
        assert len(res.json()) == 0
        # But visible if active_only=false
        res = c.get("/api/v1/portfolio/positions?active_only=false")
        assert len(res.json()) == 1


# ─── Portfolio dashboard ─────────────────────────────────────────────────────

class TestPortfolioDashboard:
    def test_empty_dashboard(self, client):
        c, _ = client
        res = c.get("/api/v1/portfolio/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["num_positions"] == 0
        assert data["summary"]["total_nav"] == 0.0

    def test_dashboard_with_positions(self, client):
        c, _ = client
        _create_position(client, ticker="NVDA", market_price=120.0, avg_cost=100.0, quantity=10, sector="Technology")
        _create_position(client, ticker="XOM", market_price=80.0, avg_cost=70.0, quantity=20, sector="Energy")

        res = c.get("/api/v1/portfolio/dashboard")
        assert res.status_code == 200
        data = res.json()
        s = data["summary"]
        assert s["num_positions"] == 2
        # NVDA: 120*10=1200, XOM: 80*20=1600 → total 2800
        assert s["invested_value"] == 2800.0
        # Unrealized: NVDA=(120-100)*10=200, XOM=(80-70)*20=200 → 400
        assert s["unrealized_pnl"] == 400.0
        # Sector breakdown should have 2 entries
        assert len(data["by_sector"]) == 2

    def test_dashboard_risk_alert_concentration(self, client):
        """Single position > 10% of NAV should trigger alert."""
        c, _ = client
        # One big position = 100% of portfolio
        _create_position(client, ticker="NVDA", market_price=100.0, avg_cost=90.0, quantity=100, sector="Tech")
        res = c.get("/api/v1/portfolio/dashboard?portfolio_value=10000")
        alerts = res.json()["summary"]["risk_alerts"]
        assert any("10%" in a for a in alerts)

    def test_dashboard_risk_alert_cash_low(self, client):
        c, _ = client
        _create_position(client, ticker="NVDA", market_price=100.0, avg_cost=90.0, quantity=10)
        res = c.get("/api/v1/portfolio/dashboard?portfolio_value=1200&cash_balance=100")
        alerts = res.json()["summary"]["risk_alerts"]
        assert any("20%" in a for a in alerts)

    def test_dashboard_sector_concentration_alert(self, client):
        """Same sector > 60% should trigger alert."""
        c, _ = client
        _create_position(client, ticker="NVDA", market_price=100.0, quantity=80, sector="Tech")
        _create_position(client, ticker="AMD", market_price=100.0, quantity=20, sector="Tech")
        res = c.get("/api/v1/portfolio/dashboard?portfolio_value=10000")
        alerts = res.json()["summary"]["risk_alerts"]
        assert any("60%" in a for a in alerts)

    def test_position_enrichment_pnl_pct(self, client):
        c, _ = client
        _create_position(client, avg_cost=100.0, market_price=120.0, quantity=10)
        res = c.get("/api/v1/portfolio/positions")
        pos = res.json()[0]
        assert pos["pnl_pct"] == 20.0  # (120-100)/100 * 100

    def test_position_enrichment_weight(self, client):
        c, _ = client
        _create_position(client, ticker="NVDA", market_price=100.0, quantity=10)  # 1000
        _create_position(client, ticker="AAPL", market_price=100.0, quantity=10)  # 1000
        res = c.get("/api/v1/portfolio/positions")
        positions = res.json()
        # Each should be ~50%
        for p in positions:
            assert p["weight_pct"] == 50.0


# ─── IB status (no connection available, but endpoint should not crash) ──────

class TestIBEndpoints:
    def test_ib_status(self, client):
        c, _ = client
        res = c.get("/api/v1/portfolio/ib/status")
        assert res.status_code == 200
        assert res.json()["connected"] is False

    def test_ib_sync_without_connection(self, client):
        c, _ = client
        res = c.post("/api/v1/portfolio/ib/sync")
        assert res.status_code == 503  # Not connected


# ─── Portfolio history ───────────────────────────────────────────────────────

class TestPortfolioHistory:
    def test_empty_history(self, client):
        c, _ = client
        res = c.get("/api/v1/portfolio/history")
        assert res.status_code == 200
        assert res.json() == []

    def test_history_after_manual_insert(self, client):
        c, Session = client
        db = Session()
        db.add(PortfolioHistory(
            total_nav=10000, cash_balance=2000, invested_value=8000,
        ))
        db.commit()
        db.close()
        res = c.get("/api/v1/portfolio/history")
        assert len(res.json()) == 1
        assert float(res.json()[0]["total_nav"]) == 10000.0
