"""
Dashboard / analytics router — /api/v1/dashboard
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import RULE_CHECKLIST
from app.database import get_db
from app.schemas.trades import DashboardResponse, RiskAlerts
from app.services.trade_analytics import (
    check_risk_alerts,
    get_analytics_summary,
    get_breakdowns,
    get_equity_curve,
    get_monthly_pnl,
)

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse, tags=["dashboard"])
def get_dashboard(
    portfolio_value: Optional[float] = Query(None, description="Current portfolio value in EUR"),
    cash_balance: Optional[float] = Query(None, description="Current cash balance in EUR"),
    db: Session = Depends(get_db),
):
    """
    Full dashboard data in a single call.
    Pass portfolio_value and cash_balance for accurate risk alerts,
    or they will be inferred from the latest daily snapshot.
    """
    summary = get_analytics_summary(db)
    equity = get_equity_curve(db)
    monthly = get_monthly_pnl(db)
    breakdowns = get_breakdowns(db)
    risk = check_risk_alerts(db, portfolio_value=portfolio_value, cash_balance=cash_balance)

    return {
        "summary": summary,
        "equity_curve": equity,
        "monthly_pnl": monthly,
        **breakdowns,
        "risk_alerts": risk["alerts"],
    }


@router.get("/dashboard/risk-alerts", response_model=RiskAlerts, tags=["dashboard"])
def get_risk_alerts(
    portfolio_value: Optional[float] = Query(None),
    cash_balance: Optional[float] = Query(None),
    db: Session = Depends(get_db),
):
    result = check_risk_alerts(db, portfolio_value=portfolio_value, cash_balance=cash_balance)
    return result


@router.get("/dashboard/rule-checklist", tags=["dashboard"])
def get_rule_checklist():
    """Return the human-readable rule checklist for the trade entry form."""
    return {"checklist": RULE_CHECKLIST}


@router.get("/dashboard/equity-curve", tags=["dashboard"])
def get_equity(db: Session = Depends(get_db)):
    return {"data": get_equity_curve(db)}


@router.get("/dashboard/monthly-pnl", tags=["dashboard"])
def get_monthly(db: Session = Depends(get_db)):
    return {"data": get_monthly_pnl(db)}


@router.get("/dashboard/breakdowns", tags=["dashboard"])
def get_breakdowns_endpoint(db: Session = Depends(get_db)):
    return get_breakdowns(db)
