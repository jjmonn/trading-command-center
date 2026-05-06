"""
Markets / Planet Alignment router — /api/v1
Handles: watchlist CRUD, heatmap, scorecard, factor refresh, LLM synthesis.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.markets import AlignmentScore, FactorSnapshot, Watchlist
from app.schemas.markets import (
    AlignmentScoreResponse,
    HeatmapEntry,
    ScorecardResponse,
    WatchlistCreate,
    WatchlistResponse,
    WatchlistUpdate,
)

router = APIRouter()

SEED_TICKERS = [
    ("NVDA", "AI infrastructure conviction"),
    ("GOOG", "Search + Cloud + AI"),
    ("AMZN", "E-commerce + AWS"),
    ("MSFT", "Cloud + AI enterprise"),
    ("WMT", "Retail defensive"),
    ("TSLA", "EV + energy"),
    ("INTC", "Chip turnaround play"),
    ("SPOT", "Audio streaming growth"),
    ("ASML", "EU semiconductor monopoly"),
    ("BNP", "EU banking sector"),
    ("CAR", "Avis Budget — rental fleet play"),
    ("VST", "Vistra Energy — power generation"),
    ("MU", "Memory semiconductor cycle"),
    ("AAPL", "Consumer tech + services"),
    ("SBUX", "Consumer discretionary turnaround"),
]


# ─── Watchlist CRUD ──────────────────────────────────────────────────────────

@router.get("/watchlist", response_model=list[WatchlistResponse], tags=["watchlist"])
def list_watchlist(
    active_only: bool = Query(True, description="Only return active tickers"),
    db: Session = Depends(get_db),
):
    q = db.query(Watchlist)
    if active_only:
        q = q.filter(Watchlist.is_active == True)  # noqa: E712
    return q.order_by(Watchlist.ticker).all()


@router.post("/watchlist", response_model=WatchlistResponse, status_code=201, tags=["watchlist"])
def add_to_watchlist(payload: WatchlistCreate, db: Session = Depends(get_db)):
    ticker = payload.ticker.upper().strip()
    existing = db.query(Watchlist).filter(Watchlist.ticker == ticker).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.notes = payload.notes or existing.notes
            existing.custom_weights = payload.custom_weights or existing.custom_weights
            db.commit()
            db.refresh(existing)
            return existing
        raise HTTPException(status_code=409, detail=f"{ticker} already in watchlist")

    item = Watchlist(
        ticker=ticker,
        notes=payload.notes,
        custom_weights=payload.custom_weights,
        is_active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/watchlist/{ticker}", response_model=WatchlistResponse, tags=["watchlist"])
def update_watchlist_item(ticker: str, payload: WatchlistUpdate, db: Session = Depends(get_db)):
    item = db.query(Watchlist).filter(Watchlist.ticker == ticker.upper()).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"{ticker.upper()} not in watchlist")

    if payload.notes is not None:
        item.notes = payload.notes
    if payload.custom_weights is not None:
        item.custom_weights = payload.custom_weights
    if payload.is_active is not None:
        item.is_active = payload.is_active
    db.commit()
    db.refresh(item)
    return item


@router.delete("/watchlist/{ticker}", status_code=204, tags=["watchlist"])
def remove_from_watchlist(ticker: str, db: Session = Depends(get_db)):
    item = db.query(Watchlist).filter(Watchlist.ticker == ticker.upper()).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"{ticker.upper()} not in watchlist")
    item.is_active = False
    db.commit()


# ─── Seed endpoint ───────────────────────────────────────────────────────────

@router.post("/watchlist/seed", response_model=list[WatchlistResponse], tags=["watchlist"])
def seed_watchlist(db: Session = Depends(get_db)):
    """Seed the watchlist with the default 15 tickers. Idempotent."""
    added = []
    for ticker, notes in SEED_TICKERS:
        existing = db.query(Watchlist).filter(Watchlist.ticker == ticker).first()
        if existing:
            if not existing.is_active:
                existing.is_active = True
                db.commit()
                db.refresh(existing)
            added.append(existing)
            continue
        item = Watchlist(ticker=ticker, notes=notes, is_active=True)
        db.add(item)
        db.commit()
        db.refresh(item)
        added.append(item)
    return added


# ─── Heatmap ─────────────────────────────────────────────────────────────────

@router.get("/markets/heatmap", response_model=list[HeatmapEntry], tags=["markets"])
def get_heatmap(db: Session = Depends(get_db)):
    """All watchlist tickers with their latest alignment scores."""
    tickers = db.query(Watchlist).filter(Watchlist.is_active == True).all()  # noqa: E712
    result = []
    for item in tickers:
        score = (
            db.query(AlignmentScore)
            .filter(AlignmentScore.ticker == item.ticker)
            .order_by(AlignmentScore.snapshot_date.desc())
            .first()
        )
        entry = HeatmapEntry(
            ticker=item.ticker,
            composite_score=score.composite_score if score else None,
            verdict=score.verdict if score else None,
            top_warnings=(score.warnings or [])[:2] if score else [],
            last_updated=score.created_at if score else None,
        )
        result.append(entry)
    return result


# ─── Scorecard ───────────────────────────────────────────────────────────────

@router.get("/markets/{ticker}", response_model=ScorecardResponse, tags=["markets"])
def get_scorecard(ticker: str, db: Session = Depends(get_db)):
    """Full scorecard for a single ticker: composite + all factor details."""
    ticker = ticker.upper()
    watchlist_item = db.query(Watchlist).filter(Watchlist.ticker == ticker).first()
    if not watchlist_item:
        raise HTTPException(status_code=404, detail=f"{ticker} not in watchlist")

    today = date.today()

    latest_score = (
        db.query(AlignmentScore)
        .filter(AlignmentScore.ticker == ticker)
        .order_by(AlignmentScore.snapshot_date.desc())
        .first()
    )

    snapshot_date = latest_score.snapshot_date if latest_score else today

    factors = (
        db.query(FactorSnapshot)
        .filter(
            FactorSnapshot.ticker == ticker,
            FactorSnapshot.snapshot_date == snapshot_date,
        )
        .all()
    )

    history_30d = (
        db.query(AlignmentScore)
        .filter(
            AlignmentScore.ticker == ticker,
            AlignmentScore.snapshot_date >= today - timedelta(days=30),
        )
        .order_by(AlignmentScore.snapshot_date)
        .all()
    )

    return ScorecardResponse(
        ticker=ticker,
        snapshot_date=snapshot_date,
        composite_score=latest_score.composite_score if latest_score else None,
        verdict=latest_score.verdict if latest_score else None,
        factor_scores=latest_score.factor_scores or {} if latest_score else {},
        factor_details=factors,
        warnings=latest_score.warnings or [] if latest_score else [],
        score_history_30d=[
            {"date": str(s.snapshot_date), "score": s.composite_score}
            for s in history_30d
        ],
        llm_synthesis=latest_score.llm_synthesis if latest_score else None,
        llm_synthesis_at=latest_score.llm_synthesis_at if latest_score else None,
    )


# ─── Score history ───────────────────────────────────────────────────────────

@router.get(
    "/markets/{ticker}/history",
    response_model=list[AlignmentScoreResponse],
    tags=["markets"],
)
def get_score_history(
    ticker: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Historical alignment scores for a ticker."""
    ticker = ticker.upper()
    cutoff = date.today() - timedelta(days=days)
    return (
        db.query(AlignmentScore)
        .filter(
            AlignmentScore.ticker == ticker,
            AlignmentScore.snapshot_date >= cutoff,
        )
        .order_by(AlignmentScore.snapshot_date)
        .all()
    )
