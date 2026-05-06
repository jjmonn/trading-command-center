"""Planet Alignment models — Phase 3."""
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Integer, JSON, String, Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    added_at = Column(DateTime, server_default=func.now())
    notes = Column(Text)
    custom_weights = Column(JSON)
    is_active = Column(Boolean, default=True)


class FactorSnapshot(Base):
    __tablename__ = "factor_snapshots"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False)
    factor_name = Column(String(30), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    raw_data = Column(JSON, nullable=False)
    score = Column(Integer)
    verdict = Column(String(10))
    explanation = Column(Text)
    source = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", "factor_name", "snapshot_date",
                         name="uq_factor_snapshot"),
    )


class AlignmentScore(Base):
    __tablename__ = "alignment_scores"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    composite_score = Column(Integer)
    verdict = Column(String(20))
    factor_scores = Column(JSON)
    warnings = Column(JSON)
    llm_synthesis = Column(Text)
    llm_synthesis_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", "snapshot_date", name="uq_alignment_score"),
    )
