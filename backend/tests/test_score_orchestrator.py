"""
Tests for score_orchestrator: score_and_persist, score_all_factors,
compute_composite, compute_alignment_score, and the refresh endpoint.
"""
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.markets import AlignmentScore, FactorSnapshot, Watchlist
from app.services.score_orchestrator import (
    compute_alignment_score,
    compute_composite,
    list_factor_names,
    score_all_factors,
    score_and_persist,
)


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


# ─── compute_composite ───────────────────────────────────────────────────────

class TestComputeComposite:
    def test_empty_returns_no_trade(self):
        result = compute_composite({})
        assert result["composite_score"] is None
        assert result["verdict"] == "no_trade"

    def test_single_neutral_factor(self):
        result = compute_composite({"valuation": 0})
        assert result["composite_score"] == 0
        assert result["verdict"] == "no_trade"

    def test_single_bullish_factor(self):
        result = compute_composite({"valuation": 50})
        assert result["composite_score"] == 50
        assert result["verdict"] == "long_bias"

    def test_strong_long_requires_5_bullish(self):
        # +50 average alone is not enough — need 5+ factors above 30
        result = compute_composite({"a": 60, "b": 60, "c": 60, "d": 60})
        assert result["composite_score"] == 60
        assert result["verdict"] == "long_bias"  # only 4 bullish

    def test_strong_long_with_5_bullish(self):
        scores = {"a": 60, "b": 60, "c": 60, "d": 60, "e": 60}
        result = compute_composite(scores)
        assert result["composite_score"] == 60
        assert result["verdict"] == "strong_long"
        assert result["bullish_count"] == 5

    def test_strong_short_requires_5_bearish(self):
        scores = {"a": -60, "b": -60, "c": -60, "d": -60, "e": -60}
        result = compute_composite(scores)
        assert result["composite_score"] == -60
        assert result["verdict"] == "strong_short"
        assert result["bearish_count"] == 5

    def test_short_bias(self):
        result = compute_composite({"a": -40, "b": -40})
        assert result["composite_score"] == -40
        assert result["verdict"] == "short_bias"

    def test_mixed_offset(self):
        # +50 and -50 → 0 → no_trade
        result = compute_composite({"a": 50, "b": -50})
        assert result["composite_score"] == 0
        assert result["verdict"] == "no_trade"

    def test_clamped_to_100(self):
        # All extreme values
        scores = {f"f{i}": 100 for i in range(5)}
        result = compute_composite(scores)
        assert result["composite_score"] == 100

    def test_excludes_none_scores(self):
        # None factors are dropped, not counted as 0
        result = compute_composite({"a": 60, "b": None, "c": 60})
        assert result["composite_score"] == 60
        assert result["bullish_count"] == 2

    def test_custom_weights(self):
        # Heavy weight on bullish factor
        result = compute_composite(
            {"valuation": 100, "technical": -100},
            weights={"valuation": 0.9, "technical": 0.1},
        )
        assert result["composite_score"] == 80

    def test_custom_weights_renormalized_when_factor_missing(self):
        # If weights specified for a factor with no score, redistribute
        result = compute_composite(
            {"valuation": 60},
            weights={"valuation": 0.5, "technical": 0.5},
        )
        assert result["composite_score"] == 60  # valuation alone, weight renormalized


# ─── score_and_persist ───────────────────────────────────────────────────────

class TestScoreAndPersist:
    def test_creates_factor_snapshot(self, client):
        _, session_cls = client
        db = session_cls()

        with patch("app.services.score_orchestrator.get_fundamentals") as mock_fund:
            mock_fund.return_value = {
                "pe_trailing": 50, "sector_pe_median": 20,
                "peg": 3.0,
            }
            snap = score_and_persist(db, "NVDA", "valuation")

        assert snap.ticker == "NVDA"
        assert snap.factor_name == "valuation"
        assert snap.score is not None
        assert snap.score < 0
        assert snap.snapshot_date == date.today()
        db.close()

    def test_uses_passed_fundamentals_no_fetch(self, client):
        _, session_cls = client
        db = session_cls()

        with patch("app.services.score_orchestrator.get_fundamentals") as mock_fund:
            snap = score_and_persist(
                db, "X", "valuation",
                fundamentals={"pe_trailing": 20, "sector_pe_median": 20},
            )
            mock_fund.assert_not_called()

        assert snap.score == 0
        db.close()

    def test_upsert_overwrites_same_day(self, client):
        _, session_cls = client
        db = session_cls()

        # First call
        score_and_persist(db, "X", "valuation",
                          fundamentals={"pe_trailing": 50, "sector_pe_median": 20, "peg": 3.0})
        # Second call same day, different data
        snap = score_and_persist(db, "X", "valuation",
                                  fundamentals={"pe_trailing": 12, "sector_pe_median": 20,
                                                "eps_trailing": 5})

        # Only one row exists for today
        all_for_today = db.query(FactorSnapshot).filter(
            FactorSnapshot.ticker == "X",
            FactorSnapshot.snapshot_date == date.today(),
        ).all()
        assert len(all_for_today) == 1
        assert snap.score > 0  # latest data
        db.close()

    def test_unknown_factor_raises(self, client):
        _, session_cls = client
        db = session_cls()
        with pytest.raises(ValueError):
            score_and_persist(db, "X", "nonexistent_factor", fundamentals={})
        db.close()

    def test_ticker_uppercased(self, client):
        _, session_cls = client
        db = session_cls()
        snap = score_and_persist(
            db, "nvda", "valuation",
            fundamentals={"pe_trailing": 20, "sector_pe_median": 20},
        )
        assert snap.ticker == "NVDA"
        db.close()


# ─── score_all_factors ──────────────────────────────────────────────────────

class TestScoreAllFactors:
    def test_runs_every_registered_factor(self, client):
        _, session_cls = client
        db = session_cls()

        with patch("app.services.score_orchestrator.get_fundamentals") as mock_fund:
            mock_fund.return_value = {"pe_trailing": 20, "sector_pe_median": 20}
            snaps = score_all_factors(db, "X")

        # Day 3: only valuation registered
        assert len(snaps) == len(list_factor_names())
        names = {s.factor_name for s in snaps}
        assert "valuation" in names
        db.close()

    def test_fundamentals_fetched_once(self, client):
        _, session_cls = client
        db = session_cls()

        with patch("app.services.score_orchestrator.get_fundamentals") as mock_fund:
            mock_fund.return_value = {"pe_trailing": 20, "sector_pe_median": 20}
            score_all_factors(db, "X")
            assert mock_fund.call_count == 1
        db.close()


# ─── compute_alignment_score ─────────────────────────────────────────────────

class TestComputeAlignmentScore:
    def test_no_factors_creates_no_trade(self, client):
        _, session_cls = client
        db = session_cls()
        score = compute_alignment_score(db, "X")
        assert score.composite_score is None
        assert score.verdict == "no_trade"
        db.close()

    def test_aggregates_factor_snapshots(self, client):
        _, session_cls = client
        db = session_cls()

        today = date.today()
        db.add(FactorSnapshot(
            ticker="X", factor_name="valuation",
            snapshot_date=today, raw_data={}, score=60, verdict="bull",
        ))
        db.commit()

        score = compute_alignment_score(db, "X")
        assert score.composite_score == 60
        assert score.verdict == "long_bias"
        assert score.factor_scores == {"valuation": 60}
        db.close()

    def test_upsert_overwrites_same_day(self, client):
        _, session_cls = client
        db = session_cls()
        today = date.today()

        # Initial factor + score
        db.add(FactorSnapshot(
            ticker="X", factor_name="valuation",
            snapshot_date=today, raw_data={}, score=60, verdict="bull",
        ))
        db.commit()
        compute_alignment_score(db, "X")

        # Update factor, recompute
        snap = db.query(FactorSnapshot).first()
        snap.score = -60
        snap.verdict = "bear"
        db.commit()
        score = compute_alignment_score(db, "X")

        all_today = db.query(AlignmentScore).filter(AlignmentScore.snapshot_date == today).all()
        assert len(all_today) == 1
        assert score.composite_score == -60
        db.close()


# ─── HTTP refresh endpoint ──────────────────────────────────────────────────

class TestRefreshEndpoint:
    def test_refresh_unknown_ticker_404(self, client):
        c, _ = client
        res = c.post("/api/v1/markets/XYZ/refresh")
        assert res.status_code == 404

    def test_refresh_runs_all_factors(self, client):
        c, _ = client
        c.post("/api/v1/watchlist", json={"ticker": "NVDA"})

        with patch("app.services.score_orchestrator.get_fundamentals") as mock_fund:
            mock_fund.return_value = {
                "pe_trailing": 50, "sector_pe_median": 20, "peg": 3.0,
            }
            res = c.post("/api/v1/markets/NVDA/refresh")

        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # at least valuation
        valuation = next(d for d in data if d["factor_name"] == "valuation")
        assert valuation["score"] is not None
        assert valuation["verdict"] in ("bull", "bear", "neutral")

    def test_refresh_then_scorecard_returns_data(self, client):
        c, _ = client
        c.post("/api/v1/watchlist", json={"ticker": "NVDA"})

        with patch("app.services.score_orchestrator.get_fundamentals") as mock_fund:
            mock_fund.return_value = {
                "pe_trailing": 50, "sector_pe_median": 20, "peg": 3.0,
            }
            c.post("/api/v1/markets/NVDA/refresh")

        scorecard = c.get("/api/v1/markets/NVDA").json()
        assert scorecard["composite_score"] is not None
        assert scorecard["verdict"] != "no_trade" or scorecard["composite_score"] is None
        assert len(scorecard["factor_details"]) >= 1


# ─── HTTP scan-all endpoint ─────────────────────────────────────────────────

class TestScanAllEndpoint:
    def test_scan_all_empty_watchlist(self, client):
        c, _ = client
        res = c.post("/api/v1/markets/scan-all")
        assert res.status_code == 200
        assert res.json()["scanned"] == 0
        assert res.json()["total"] == 0

    def test_scan_all_processes_watchlist(self, client):
        c, _ = client
        c.post("/api/v1/watchlist", json={"ticker": "NVDA"})
        c.post("/api/v1/watchlist", json={"ticker": "GOOG"})

        with patch("app.services.score_orchestrator.get_fundamentals") as mock_fund:
            mock_fund.return_value = {"pe_trailing": 20, "sector_pe_median": 20}
            res = c.post("/api/v1/markets/scan-all")

        data = res.json()
        assert data["scanned"] == 2
        assert data["total"] == 2
        assert data["errors"] == []
        assert "valuation" in data["factors"]

    def test_heatmap_after_scan_has_scores(self, client):
        c, _ = client
        c.post("/api/v1/watchlist", json={"ticker": "NVDA"})

        with patch("app.services.score_orchestrator.get_fundamentals") as mock_fund:
            mock_fund.return_value = {"pe_trailing": 20, "sector_pe_median": 20}
            c.post("/api/v1/markets/scan-all")

        heatmap = c.get("/api/v1/markets/heatmap").json()
        assert len(heatmap) == 1
        assert heatmap[0]["composite_score"] is not None
        assert heatmap[0]["verdict"] is not None
