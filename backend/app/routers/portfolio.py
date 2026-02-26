"""
Portfolio / Positions router — /api/v1/portfolio
Handles: manual position CRUD, IB sync, portfolio summary, exposure analysis.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.portfolio import PortfolioHistory, Position
from app.schemas.portfolio import (
    ExposureBreakdown,
    IBStatus,
    PortfolioDashboard,
    PortfolioHistoryResponse,
    PortfolioSummary,
    PositionCreate,
    PositionResponse,
    PositionUpdate,
)
from app.services.ib_connector import get_ib_connector
from app.services.price_fetcher import get_batch_prices

router = APIRouter()


# ─── IB connection ───────────────────────────────────────────────────────────

@router.get("/portfolio/ib/status", response_model=IBStatus, tags=["portfolio"])
def ib_status():
    """Check IB connection status."""
    connector = get_ib_connector()
    s = connector.get_status()
    return s


@router.post("/portfolio/ib/connect", response_model=IBStatus, tags=["portfolio"])
def ib_connect():
    """Attempt to connect to IB TWS/Gateway."""
    connector = get_ib_connector()
    result = connector.connect()
    return {**result, "host": connector.host, "port": connector.port}


@router.post("/portfolio/ib/disconnect", response_model=IBStatus, tags=["portfolio"])
def ib_disconnect():
    """Disconnect from IB."""
    connector = get_ib_connector()
    connector.disconnect()
    return {
        "connected": False,
        "host": connector.host,
        "port": connector.port,
        "message": "Disconnected",
    }


@router.post("/portfolio/ib/sync", tags=["portfolio"])
def ib_sync_positions(db: Session = Depends(get_db)):
    """
    Pull current positions from IB and upsert into the positions table.
    Marks IB positions that no longer exist as inactive.
    """
    connector = get_ib_connector()
    if not connector.is_connected:
        raise HTTPException(status_code=503, detail="Not connected to IB")

    ib_positions = connector.get_positions()

    # Track which ib_con_ids we see this sync
    seen_con_ids: set[int] = set()

    synced = []
    for ib_pos in ib_positions:
        con_id = ib_pos["ib_con_id"]
        seen_con_ids.add(con_id)

        existing = db.query(Position).filter(Position.ib_con_id == con_id).first()
        if existing:
            # Update existing
            existing.quantity = ib_pos["quantity"]
            existing.avg_cost = ib_pos["avg_cost"]
            existing.market_price = ib_pos["market_price"]
            existing.market_value = ib_pos["market_value"]
            existing.unrealized_pnl = ib_pos["unrealized_pnl"]
            existing.realized_pnl = ib_pos["realized_pnl"]
            existing.is_active = True
            existing.last_updated = datetime.utcnow()
            synced.append(existing.id)
        else:
            # Create new
            pos = Position(
                ib_con_id=con_id,
                ticker=ib_pos["ticker"],
                instrument_type=ib_pos["instrument_type"],
                quantity=ib_pos["quantity"],
                avg_cost=ib_pos["avg_cost"],
                market_price=ib_pos["market_price"],
                market_value=ib_pos["market_value"],
                unrealized_pnl=ib_pos["unrealized_pnl"],
                realized_pnl=ib_pos["realized_pnl"],
                currency=ib_pos["currency"],
                strike=ib_pos.get("strike"),
                expiry=ib_pos.get("expiry"),
                option_type=ib_pos.get("option_type"),
                source="ib",
                is_active=True,
            )
            db.add(pos)
            db.flush()
            synced.append(pos.id)

    # Mark old IB positions as inactive
    ib_positions_in_db = (
        db.query(Position)
        .filter(Position.source == "ib", Position.is_active.is_(True))
        .all()
    )
    for p in ib_positions_in_db:
        if p.ib_con_id and p.ib_con_id not in seen_con_ids:
            p.is_active = False

    # Save portfolio history snapshot
    acct = connector.get_account_values()
    if acct:
        snapshot = PortfolioHistory(
            total_nav=acct.get("NetLiquidation"),
            cash_balance=acct.get("TotalCashValue"),
            invested_value=acct.get("GrossPositionValue"),
            unrealized_pnl=acct.get("UnrealizedPnL"),
            margin_used=acct.get("MaintMarginReq"),
            buying_power=acct.get("BuyingPower"),
        )
        db.add(snapshot)

    db.commit()
    return {"synced_count": len(synced), "synced_ids": synced}


# ─── Manual position CRUD ────────────────────────────────────────────────────

@router.get("/portfolio/positions", response_model=list[PositionResponse], tags=["portfolio"])
def list_positions(
    active_only: bool = Query(True),
    source: Optional[str] = Query(None, description="ib | manual"),
    db: Session = Depends(get_db),
):
    q = db.query(Position)
    if active_only:
        q = q.filter(Position.is_active.is_(True))
    if source:
        q = q.filter(Position.source == source)
    positions = q.order_by(Position.ticker).all()

    # Enrich with computed fields
    total_value = sum(float(p.market_value or 0) for p in positions)
    result = []
    for p in positions:
        resp = PositionResponse.model_validate(p)
        # P&L %
        if p.avg_cost and p.market_price and float(p.avg_cost) > 0:
            resp.pnl_pct = round(
                (float(p.market_price) - float(p.avg_cost)) / float(p.avg_cost) * 100, 2
            )
        # DTE
        if p.expiry:
            expiry_date = p.expiry if isinstance(p.expiry, date) else date.fromisoformat(str(p.expiry)[:10])
            resp.dte = (expiry_date - date.today()).days
        # Weight
        if total_value > 0:
            resp.weight_pct = round(abs(float(p.market_value or 0)) / total_value * 100, 1)
        result.append(resp)

    return result


@router.post("/portfolio/positions", response_model=PositionResponse, status_code=201, tags=["portfolio"])
def create_position(payload: PositionCreate, db: Session = Depends(get_db)):
    """Create a manual position (for non-IB holdings)."""
    pos = Position(
        ticker=payload.ticker.upper().strip(),
        instrument_type=payload.instrument_type,
        quantity=payload.quantity,
        avg_cost=payload.avg_cost,
        market_price=payload.market_price,
        currency=payload.currency,
        strike=payload.strike,
        expiry=payload.expiry,
        option_type=payload.option_type,
        sector=payload.sector,
        notes=payload.notes,
        source="manual",
        is_active=True,
    )
    # Compute market value if possible
    if payload.market_price and payload.quantity:
        pos.market_value = Decimal(str(float(payload.market_price) * float(payload.quantity)))
    if payload.avg_cost and payload.market_price and payload.quantity:
        pos.unrealized_pnl = Decimal(str(
            (float(payload.market_price) - float(payload.avg_cost)) * float(payload.quantity)
        ))

    db.add(pos)
    db.commit()
    db.refresh(pos)
    return pos


@router.get("/portfolio/positions/{position_id}", response_model=PositionResponse, tags=["portfolio"])
def get_position(position_id: int, db: Session = Depends(get_db)):
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    return pos


@router.patch("/portfolio/positions/{position_id}", response_model=PositionResponse, tags=["portfolio"])
def update_position(position_id: int, payload: PositionUpdate, db: Session = Depends(get_db)):
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(pos, field, value)
    pos.last_updated = datetime.utcnow()

    # Recompute market_value and unrealized_pnl
    qty = float(pos.quantity or 0)
    mp = float(pos.market_price or 0)
    ac = float(pos.avg_cost or 0)
    if mp and qty:
        pos.market_value = Decimal(str(round(mp * qty, 2)))
    if ac and mp and qty:
        pos.unrealized_pnl = Decimal(str(round((mp - ac) * qty, 2)))

    db.commit()
    db.refresh(pos)
    return pos


@router.delete("/portfolio/positions/{position_id}", status_code=204, tags=["portfolio"])
def delete_position(position_id: int, db: Session = Depends(get_db)):
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    db.delete(pos)
    db.commit()


# ─── Price refresh ───────────────────────────────────────────────────────────

@router.post("/portfolio/refresh-prices", tags=["portfolio"])
def refresh_prices(db: Session = Depends(get_db)):
    """
    Update market_price for all active positions using yfinance.
    Useful for manual positions or when IB is disconnected.
    """
    positions = db.query(Position).filter(Position.is_active.is_(True)).all()
    if not positions:
        return {"updated": 0}

    tickers = list({p.ticker for p in positions})
    prices = get_batch_prices(tickers)

    updated = 0
    for p in positions:
        price = prices.get(p.ticker)
        if price is not None:
            p.market_price = Decimal(str(round(price, 4)))
            qty = float(p.quantity or 0)
            p.market_value = Decimal(str(round(price * qty, 2)))
            if p.avg_cost and float(p.avg_cost) > 0:
                p.unrealized_pnl = Decimal(str(round((price - float(p.avg_cost)) * qty, 2)))
            p.last_updated = datetime.utcnow()
            updated += 1

    db.commit()
    return {"updated": updated, "total": len(positions), "prices": prices}


# ─── Portfolio dashboard ─────────────────────────────────────────────────────

@router.get("/portfolio/dashboard", response_model=PortfolioDashboard, tags=["portfolio"])
def portfolio_dashboard(
    portfolio_value: Optional[float] = Query(None, description="Override total NAV"),
    cash_balance: Optional[float] = Query(None, description="Override cash balance"),
    db: Session = Depends(get_db),
):
    """Full portfolio dashboard in a single call."""
    positions = (
        db.query(Position)
        .filter(Position.is_active.is_(True))
        .order_by(Position.ticker)
        .all()
    )

    # Compute totals
    total_market_value = sum(float(p.market_value or 0) for p in positions)
    total_unrealized = sum(float(p.unrealized_pnl or 0) for p in positions)
    total_long = sum(
        float(p.market_value or 0) for p in positions if float(p.quantity or 0) > 0
    )
    total_short = sum(
        abs(float(p.market_value or 0)) for p in positions if float(p.quantity or 0) < 0
    )

    nav = portfolio_value or total_market_value
    cash = cash_balance or max(0, nav - total_market_value)
    invested = total_market_value
    cash_pct = (cash / nav * 100) if nav > 0 else 100.0
    leverage = (total_long + total_short) / nav if nav > 0 else 0.0

    # Risk alerts
    alerts: list[str] = []
    if nav > 0 and cash_pct < 20:
        alerts.append(f"Cash reserve {cash_pct:.1f}% is below the 20% minimum")
    # Check single-position concentration
    for p in positions:
        mv = abs(float(p.market_value or 0))
        if nav > 0 and mv / nav > 0.10:
            alerts.append(f"{p.ticker} is {mv/nav*100:.1f}% of portfolio (>10% limit)")
    # Check sector concentration
    sector_totals: dict[str, float] = defaultdict(float)
    for p in positions:
        sec = p.sector or "Unknown"
        sector_totals[sec] += abs(float(p.market_value or 0))
    for sec, val in sector_totals.items():
        if nav > 0 and val / nav > 0.60:
            alerts.append(f"Sector '{sec}' is {val/nav*100:.1f}% of portfolio (>60% limit)")

    summary = PortfolioSummary(
        total_nav=round(nav, 2),
        cash_balance=round(cash, 2),
        invested_value=round(invested, 2),
        unrealized_pnl=round(total_unrealized, 2),
        total_long_exposure=round(total_long, 2),
        total_short_exposure=round(total_short, 2),
        net_exposure=round(total_long - total_short, 2),
        cash_pct=round(cash_pct, 1),
        leverage_ratio=round(leverage, 2),
        num_positions=len(positions),
        risk_alerts=alerts,
    )

    # Enriched positions
    pos_responses = []
    for p in positions:
        resp = PositionResponse.model_validate(p)
        if p.avg_cost and p.market_price and float(p.avg_cost) > 0:
            resp.pnl_pct = round(
                (float(p.market_price) - float(p.avg_cost)) / float(p.avg_cost) * 100, 2
            )
        if p.expiry:
            expiry_date = p.expiry if isinstance(p.expiry, date) else date.fromisoformat(str(p.expiry)[:10])
            resp.dte = (expiry_date - date.today()).days
        if total_market_value > 0:
            resp.weight_pct = round(abs(float(p.market_value or 0)) / total_market_value * 100, 1)
        pos_responses.append(resp)

    # Breakdowns
    def _breakdown(attr: str) -> list[ExposureBreakdown]:
        groups: dict[str, float] = defaultdict(float)
        for p in positions:
            key = getattr(p, attr) or "Unknown"
            groups[key] += abs(float(p.market_value or 0))
        total = sum(groups.values()) or 1
        return sorted(
            [ExposureBreakdown(label=k, value=round(v, 2), pct=round(v / total * 100, 1))
             for k, v in groups.items()],
            key=lambda x: x.value,
            reverse=True,
        )

    by_sector = _breakdown("sector")
    by_instrument = _breakdown("instrument_type")
    by_currency = _breakdown("currency")

    # History (last 90 entries)
    history = (
        db.query(PortfolioHistory)
        .order_by(PortfolioHistory.timestamp.desc())
        .limit(90)
        .all()
    )

    return PortfolioDashboard(
        summary=summary,
        positions=pos_responses,
        by_sector=by_sector,
        by_instrument=by_instrument,
        by_currency=by_currency,
        history=list(reversed(history)),
    )


# ─── Portfolio history ───────────────────────────────────────────────────────

@router.get("/portfolio/history", response_model=list[PortfolioHistoryResponse], tags=["portfolio"])
def portfolio_history(
    limit: int = Query(90, le=365),
    db: Session = Depends(get_db),
):
    return (
        db.query(PortfolioHistory)
        .order_by(PortfolioHistory.timestamp.desc())
        .limit(limit)
        .all()
    )
