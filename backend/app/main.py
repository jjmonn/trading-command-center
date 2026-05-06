import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import STRATEGY_RULES_V1, settings
from app.database import SessionLocal, engine
from app.models import trades as _trade_models  # ensure models are registered
from app.models import social as _social_models  # noqa: F401
from app.models import markets as _market_models  # noqa: F401
from app.routers import dashboard, markets, portfolio, trades

logging.basicConfig(level=settings.log_level.upper())
log = logging.getLogger(__name__)

app = FastAPI(
    title="Trading Command Center",
    description="Options trading system for a European retail trader.",
    version="0.1.0",
)

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(trades.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(markets.router, prefix="/api/v1")


# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    """
    Create all tables (Alembic is preferred in production — this is a dev fallback).
    Also seed strategy rules v1 if not present.
    """
    from app.database import Base
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        from app.models.trades import StrategyRules
        if not db.query(StrategyRules).filter(StrategyRules.version == 1).first():
            db.add(StrategyRules(version=1, rules_json=STRATEGY_RULES_V1, notes="Initial rules"))
            db.commit()
            log.info("Seeded strategy rules v1")
    finally:
        db.close()


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "env": settings.app_env}
