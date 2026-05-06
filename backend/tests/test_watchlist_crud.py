"""
Tests for Planet Alignment: watchlist CRUD, heatmap, scorecard, seed, history.
"""
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.markets import AlignmentScore, FactorSnapshot, Watchlist


# ─── Test DB fixture ─────────────────────────────────────────────────────────

@pytest.fixture()
def client():
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


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _add_ticker(client_tuple, ticker="NVDA", notes=None):
    client, _ = client_tuple
    payload = {"ticker": ticker}
    if notes:
        payload["notes"] = notes
    return client.post("/api/v1/watchlist", json=payload)


# ═══════════════════════════════════════════════════════════════════════════
# Watchlist CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestWatchlistAdd:
    def test_add_ticker(self, client):
        res = _add_ticker(client, "NVDA", "AI play")
        assert res.status_code == 201
        data = res.json()
        assert data["ticker"] == "NVDA"
        assert data["notes"] == "AI play"
        assert data["is_active"] is True

    def test_add_ticker_uppercase(self, client):
        res = _add_ticker(client, "nvda")
        assert res.status_code == 201
        assert res.json()["ticker"] == "NVDA"

    def test_add_duplicate_returns_409(self, client):
        _add_ticker(client, "NVDA")
        res = _add_ticker(client, "NVDA")
        assert res.status_code == 409

    def test_add_reactivates_inactive(self, client):
        c, _ = client
        _add_ticker(client, "NVDA")
        c.delete("/api/v1/watchlist/NVDA")
        res = _add_ticker(client, "NVDA")
        assert res.status_code == 201
        assert res.json()["is_active"] is True

    def test_add_with_custom_weights(self, client):
        c, _ = client
        res = c.post("/api/v1/watchlist", json={
            "ticker": "TSLA",
            "custom_weights": {"valuation": 0.3, "technical": 0.2},
        })
        assert res.status_code == 201
        assert res.json()["custom_weights"]["valuation"] == 0.3

    def test_add_empty_ticker_fails(self, client):
        c, _ = client
        res = c.post("/api/v1/watchlist", json={"ticker": ""})
        assert res.status_code == 422


class TestWatchlistList:
    def test_list_empty(self, client):
        c, _ = client
        res = c.get("/api/v1/watchlist")
        assert res.status_code == 200
        assert res.json() == []

    def test_list_returns_active_only_by_default(self, client):
        c, _ = client
        _add_ticker(client, "NVDA")
        _add_ticker(client, "GOOG")
        c.delete("/api/v1/watchlist/GOOG")
        res = c.get("/api/v1/watchlist")
        assert len(res.json()) == 1
        assert res.json()[0]["ticker"] == "NVDA"

    def test_list_all_includes_inactive(self, client):
        c, _ = client
        _add_ticker(client, "NVDA")
        _add_ticker(client, "GOOG")
        c.delete("/api/v1/watchlist/GOOG")
        res = c.get("/api/v1/watchlist?active_only=false")
        assert len(res.json()) == 2

    def test_list_sorted_alphabetically(self, client):
        for t in ["TSLA", "AAPL", "MSFT"]:
            _add_ticker(client, t)
        c, _ = client
        data = c.get("/api/v1/watchlist").json()
        tickers = [d["ticker"] for d in data]
        assert tickers == ["AAPL", "MSFT", "TSLA"]


class TestWatchlistUpdate:
    def test_update_notes(self, client):
        c, _ = client
        _add_ticker(client, "NVDA")
        res = c.patch("/api/v1/watchlist/NVDA", json={"notes": "Updated note"})
        assert res.status_code == 200
        assert res.json()["notes"] == "Updated note"

    def test_update_custom_weights(self, client):
        c, _ = client
        _add_ticker(client, "NVDA")
        res = c.patch("/api/v1/watchlist/NVDA", json={
            "custom_weights": {"valuation": 0.25, "technical": 0.15},
        })
        assert res.status_code == 200
        assert res.json()["custom_weights"]["valuation"] == 0.25

    def test_update_is_active(self, client):
        c, _ = client
        _add_ticker(client, "NVDA")
        res = c.patch("/api/v1/watchlist/NVDA", json={"is_active": False})
        assert res.status_code == 200
        assert res.json()["is_active"] is False

    def test_update_nonexistent_returns_404(self, client):
        c, _ = client
        res = c.patch("/api/v1/watchlist/XYZ", json={"notes": "test"})
        assert res.status_code == 404

    def test_update_case_insensitive(self, client):
        c, _ = client
        _add_ticker(client, "NVDA")
        res = c.patch("/api/v1/watchlist/nvda", json={"notes": "lower"})
        assert res.status_code == 200


class TestWatchlistDelete:
    def test_delete_sets_inactive(self, client):
        c, _ = client
        _add_ticker(client, "NVDA")
        res = c.delete("/api/v1/watchlist/NVDA")
        assert res.status_code == 204

        data = c.get("/api/v1/watchlist?active_only=false").json()
        assert len(data) == 1
        assert data[0]["is_active"] is False

    def test_delete_nonexistent_returns_404(self, client):
        c, _ = client
        res = c.delete("/api/v1/watchlist/XYZ")
        assert res.status_code == 404

    def test_delete_case_insensitive(self, client):
        c, _ = client
        _add_ticker(client, "NVDA")
        res = c.delete("/api/v1/watchlist/nvda")
        assert res.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════
# Seed endpoint
# ═══════════════════════════════════════════════════════════════════════════

class TestSeed:
    def test_seed_creates_15_tickers(self, client):
        c, _ = client
        res = c.post("/api/v1/watchlist/seed")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 15
        tickers = {d["ticker"] for d in data}
        assert "NVDA" in tickers
        assert "SBUX" in tickers

    def test_seed_is_idempotent(self, client):
        c, _ = client
        c.post("/api/v1/watchlist/seed")
        c.post("/api/v1/watchlist/seed")
        data = c.get("/api/v1/watchlist").json()
        assert len(data) == 15

    def test_seed_reactivates_deleted(self, client):
        c, _ = client
        c.post("/api/v1/watchlist/seed")
        c.delete("/api/v1/watchlist/NVDA")
        c.post("/api/v1/watchlist/seed")
        data = c.get("/api/v1/watchlist").json()
        tickers = {d["ticker"] for d in data}
        assert "NVDA" in tickers


# ═══════════════════════════════════════════════════════════════════════════
# Heatmap
# ═══════════════════════════════════════════════════════════════════════════

class TestHeatmap:
    def test_heatmap_empty(self, client):
        c, _ = client
        res = c.get("/api/v1/markets/heatmap")
        assert res.status_code == 200
        assert res.json() == []

    def test_heatmap_returns_tickers_without_scores(self, client):
        c, _ = client
        _add_ticker(client, "NVDA")
        _add_ticker(client, "GOOG")
        data = c.get("/api/v1/markets/heatmap").json()
        assert len(data) == 2
        assert data[0]["composite_score"] is None
        assert data[0]["verdict"] is None

    def test_heatmap_with_scores(self, client):
        c, session_cls = client
        _add_ticker(client, "NVDA")

        db = session_cls()
        db.add(AlignmentScore(
            ticker="NVDA",
            snapshot_date=date.today(),
            composite_score=65,
            verdict="strong_long",
            factor_scores={"valuation": -20, "technical": 80},
            warnings=["near_earnings", "high_iv", "extra_warning"],
        ))
        db.commit()
        db.close()

        data = c.get("/api/v1/markets/heatmap").json()
        assert len(data) == 1
        assert data[0]["composite_score"] == 65
        assert data[0]["verdict"] == "strong_long"
        assert len(data[0]["top_warnings"]) == 2

    def test_heatmap_excludes_inactive(self, client):
        c, _ = client
        _add_ticker(client, "NVDA")
        _add_ticker(client, "GOOG")
        c.delete("/api/v1/watchlist/GOOG")
        data = c.get("/api/v1/markets/heatmap").json()
        assert len(data) == 1


# ═══════════════════════════════════════════════════════════════════════════
# Scorecard
# ═══════════════════════════════════════════════════════════════════════════

class TestScorecard:
    def test_scorecard_not_in_watchlist(self, client):
        c, _ = client
        res = c.get("/api/v1/markets/XYZ")
        assert res.status_code == 404

    def test_scorecard_empty(self, client):
        c, _ = client
        _add_ticker(client, "NVDA")
        res = c.get("/api/v1/markets/NVDA")
        assert res.status_code == 200
        data = res.json()
        assert data["ticker"] == "NVDA"
        assert data["composite_score"] is None
        assert data["factor_details"] == []

    def test_scorecard_with_data(self, client):
        c, session_cls = client
        _add_ticker(client, "NVDA")

        db = session_cls()
        today = date.today()
        db.add(AlignmentScore(
            ticker="NVDA",
            snapshot_date=today,
            composite_score=42,
            verdict="long_bias",
            factor_scores={"valuation": -10, "technical": 60, "sector_trend": 30},
            warnings=["near_earnings"],
        ))
        db.add(FactorSnapshot(
            ticker="NVDA",
            factor_name="valuation",
            snapshot_date=today,
            raw_data={"pe": 48, "pe_sector_median": 25},
            score=-10,
            verdict="neutral",
            explanation="P/E near sector average",
            source="yfinance",
        ))
        db.add(FactorSnapshot(
            ticker="NVDA",
            factor_name="technical",
            snapshot_date=today,
            raw_data={"rsi": 55, "dist_50ma": 3.2},
            score=60,
            verdict="bull",
            explanation="Healthy uptrend above MAs",
            source="yfinance",
        ))
        db.commit()
        db.close()

        data = c.get("/api/v1/markets/NVDA").json()
        assert data["composite_score"] == 42
        assert data["verdict"] == "long_bias"
        assert len(data["factor_details"]) == 2
        assert data["warnings"] == ["near_earnings"]

    def test_scorecard_case_insensitive(self, client):
        c, _ = client
        _add_ticker(client, "NVDA")
        res = c.get("/api/v1/markets/nvda")
        assert res.status_code == 200
        assert res.json()["ticker"] == "NVDA"


# ═══════════════════════════════════════════════════════════════════════════
# Score history
# ═══════════════════════════════════════════════════════════════════════════

class TestScoreHistory:
    def test_history_empty(self, client):
        c, _ = client
        res = c.get("/api/v1/markets/NVDA/history")
        assert res.status_code == 200
        assert res.json() == []

    def test_history_returns_recent(self, client):
        c, session_cls = client
        db = session_cls()
        today = date.today()
        for i in range(5):
            db.add(AlignmentScore(
                ticker="NVDA",
                snapshot_date=today - timedelta(days=i),
                composite_score=50 - i * 10,
                verdict="long_bias",
            ))
        db.commit()
        db.close()

        data = c.get("/api/v1/markets/NVDA/history").json()
        assert len(data) == 5
        assert data[0]["snapshot_date"] == str(today - timedelta(days=4))
        assert data[-1]["snapshot_date"] == str(today)

    def test_history_respects_days_param(self, client):
        c, session_cls = client
        db = session_cls()
        today = date.today()
        for i in range(40):
            db.add(AlignmentScore(
                ticker="NVDA",
                snapshot_date=today - timedelta(days=i),
                composite_score=50,
                verdict="long_bias",
            ))
        db.commit()
        db.close()

        data_30 = c.get("/api/v1/markets/NVDA/history?days=30").json()
        data_7 = c.get("/api/v1/markets/NVDA/history?days=7").json()
        assert len(data_30) == 31  # today + 30 days back
        assert len(data_7) == 8
