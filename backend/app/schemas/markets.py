"""Pydantic schemas for Planet Alignment."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class WatchlistCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    notes: Optional[str] = None
    custom_weights: Optional[dict[str, float]] = None


class WatchlistUpdate(BaseModel):
    notes: Optional[str] = None
    custom_weights: Optional[dict[str, float]] = None
    is_active: Optional[bool] = None


class WatchlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticker: str
    added_at: datetime
    notes: Optional[str] = None
    custom_weights: Optional[dict[str, float]] = None
    is_active: bool


class FactorSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    factor_name: str
    snapshot_date: date
    raw_data: dict[str, Any]
    score: Optional[int] = None
    verdict: Optional[str] = None
    explanation: Optional[str] = None
    source: Optional[str] = None


class AlignmentScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ticker: str
    snapshot_date: date
    composite_score: Optional[int] = None
    verdict: Optional[str] = None
    factor_scores: Optional[dict[str, int]] = None
    warnings: Optional[list[str]] = None
    llm_synthesis: Optional[str] = None
    llm_synthesis_at: Optional[datetime] = None


class HeatmapEntry(BaseModel):
    """One row of the heatmap view."""
    ticker: str
    current_price: Optional[float] = None
    composite_score: Optional[int] = None
    verdict: Optional[str] = None
    top_warnings: list[str] = Field(default_factory=list)
    last_updated: Optional[datetime] = None


class ScorecardResponse(BaseModel):
    """Full scorecard for one ticker."""
    ticker: str
    sector: Optional[str] = None
    current_price: Optional[float] = None
    snapshot_date: date
    composite_score: Optional[int] = None
    verdict: Optional[str] = None
    factor_scores: dict[str, int] = Field(default_factory=dict)
    factor_details: list[FactorSnapshotResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    score_history_30d: list[dict] = Field(default_factory=list)
    llm_synthesis: Optional[str] = None
    llm_synthesis_at: Optional[datetime] = None
