"""
Trade CRUD router — /api/v1/trades
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.trades import DailySnapshot, StrategyRules, Trade
from app.schemas.trades import (
    DailySnapshotCreate,
    DailySnapshotResponse,
    StrategyRulesCreate,
    StrategyRulesResponse,
    TradeClose,
    TradeCreate,
    TradeResponse,
    TradeUpdate,
)
from app.services.trade_analytics import compute_trade_pnl

router = APIRouter()


# ─── Strategy rules endpoints ─────────────────────────────────────────────────

@router.get("/strategy-rules", response_model=list[StrategyRulesResponse], tags=["strategy"])
def list_strategy_rules(db: Session = Depends(get_db)):
    return db.query(StrategyRules).order_by(StrategyRules.version.desc()).all()


@router.get("/strategy-rules/current", response_model=StrategyRulesResponse, tags=["strategy"])
def get_current_rules(db: Session = Depends(get_db)):
    rules = db.query(StrategyRules).order_by(StrategyRules.version.desc()).first()
    if not rules:
        raise HTTPException(status_code=404, detail="No strategy rules found")
    return rules


@router.post("/strategy-rules", response_model=StrategyRulesResponse, status_code=201, tags=["strategy"])
def create_strategy_rules(payload: StrategyRulesCreate, db: Session = Depends(get_db)):
    existing = db.query(StrategyRules).filter(StrategyRules.version == payload.version).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Version {payload.version} already exists")
    rules = StrategyRules(**payload.model_dump())
    db.add(rules)
    db.commit()
    db.refresh(rules)
    return rules


# ─── Trade CRUD ───────────────────────────────────────────────────────────────

@router.post("/trades", response_model=TradeResponse, status_code=201, tags=["trades"])
def create_trade(payload: TradeCreate, db: Session = Depends(get_db)):
    # Attach latest strategy rules version if not specified
    if payload.strategy_rules_version is None:
        latest = db.query(StrategyRules).order_by(StrategyRules.version.desc()).first()
        if latest:
            payload = payload.model_copy(update={"strategy_rules_version": latest.version})

    trade = Trade(**payload.model_dump())
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


@router.get("/trades", response_model=list[TradeResponse], tags=["trades"])
def list_trades(
    status: Optional[str] = Query(None, description="Filter by status: open|closed|expired"),
    ticker: Optional[str] = Query(None),
    instrument_type: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    strategy_category: Optional[str] = Query(None),
    news_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    sort_by: str = Query("entry_datetime"),
    sort_dir: str = Query("desc"),
    db: Session = Depends(get_db),
):
    q = db.query(Trade)

    if status:
        q = q.filter(Trade.status == status)
    if ticker:
        q = q.filter(Trade.ticker == ticker.upper())
    if instrument_type:
        q = q.filter(Trade.instrument_type == instrument_type)
    if sector:
        q = q.filter(Trade.sector.ilike(f"%{sector}%"))
    if strategy_category:
        q = q.filter(Trade.strategy_category == strategy_category)
    if news_type:
        q = q.filter(Trade.news_type == news_type)
    if date_from:
        q = q.filter(Trade.entry_datetime >= date_from)
    if date_to:
        q = q.filter(Trade.entry_datetime <= date_to)

    col = getattr(Trade, sort_by, Trade.entry_datetime)
    q = q.order_by(col.desc() if sort_dir == "desc" else col.asc())

    return q.offset(offset).limit(limit).all()


@router.get("/trades/{trade_id}", response_model=TradeResponse, tags=["trades"])
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.patch("/trades/{trade_id}", response_model=TradeResponse, tags=["trades"])
def update_trade(trade_id: int, payload: TradeUpdate, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(trade, field, value)
    trade.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(trade)
    return trade


@router.post("/trades/{trade_id}/close", response_model=TradeResponse, tags=["trades"])
def close_trade(trade_id: int, payload: TradeClose, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.status == "closed":
        raise HTTPException(status_code=409, detail="Trade is already closed")

    # Compute P&L
    pnl = compute_trade_pnl(
        entry_price=float(trade.entry_price),
        exit_price=float(payload.exit_price),
        quantity=trade.quantity,
        fees_entry=float(trade.fees_entry or 0),
        fees_exit=float(payload.fees_exit or 0),
        instrument_type=trade.instrument_type,
    )

    # Compute duration
    exit_dt = payload.exit_datetime or datetime.utcnow()
    duration_hours = (exit_dt - trade.entry_datetime).total_seconds() / 3600

    # Apply all updates
    trade.exit_price = payload.exit_price
    trade.exit_datetime = exit_dt
    trade.fees_exit = payload.fees_exit
    trade.fx_rate_exit = payload.fx_rate_exit
    trade.exit_reason = payload.exit_reason
    trade.emotional_state_exit = payload.emotional_state_exit
    trade.notes_what_worked = payload.notes_what_worked
    trade.notes_what_didnt = payload.notes_what_didnt
    trade.lessons_learned = payload.lessons_learned
    trade.would_take_again = payload.would_take_again
    trade.max_favorable_excursion = payload.max_favorable_excursion
    trade.max_adverse_excursion = payload.max_adverse_excursion
    trade.gross_pnl = pnl["gross_pnl"]
    trade.net_pnl = pnl["net_pnl"]
    trade.gross_pnl_pct = pnl["gross_pnl_pct"]
    trade.net_pnl_pct = pnl["net_pnl_pct"]
    trade.duration_hours = round(duration_hours, 2)
    trade.status = "closed"
    trade.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(trade)
    return trade


@router.delete("/trades/{trade_id}", status_code=204, tags=["trades"])
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    db.delete(trade)
    db.commit()


# ─── Daily snapshots ──────────────────────────────────────────────────────────

@router.post("/snapshots", response_model=DailySnapshotResponse, status_code=201, tags=["portfolio"])
def create_snapshot(payload: DailySnapshotCreate, db: Session = Depends(get_db)):
    existing = db.query(DailySnapshot).filter(DailySnapshot.date == payload.date).first()
    if existing:
        # Upsert: update existing
        for field, value in payload.model_dump().items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing
    snap = DailySnapshot(**payload.model_dump())
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


@router.get("/snapshots", response_model=list[DailySnapshotResponse], tags=["portfolio"])
def list_snapshots(
    limit: int = Query(90, le=365),
    db: Session = Depends(get_db),
):
    return (
        db.query(DailySnapshot)
        .order_by(DailySnapshot.date.desc())
        .limit(limit)
        .all()
    )
