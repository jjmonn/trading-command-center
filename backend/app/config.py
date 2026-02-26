from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Database
    database_url: str = "sqlite:///./trading.db"
    redis_url: str = "redis://localhost:6379"

    # Interactive Brokers
    ib_host: str = "127.0.0.1"
    ib_port: int = 7497
    ib_client_id: int = 1

    # APIs
    anthropic_api_key: Optional[str] = None
    unusual_whales_api_key: Optional[str] = None
    news_api_key: Optional[str] = None
    alpha_vantage_key: Optional[str] = None

    # Reddit
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    portfolio_currency: str = "EUR"


settings = Settings()

# ─── Strategy Rules (versioned) ────────────────────────────────────────────────

STRATEGY_RULES_V1: dict = {
    "version": 1,
    "entry": {
        "news_types_allowed": [
            "earnings", "buyback", "analyst_upgrade", "analyst_downgrade",
            "geopolitical", "sector_news", "guidance", "product_launch",
            "regulatory", "technical_setup", "flow_signal",
        ],
        "min_expected_move_pct": 2.0,
        "market_trend_filter": True,
        "sector_trend_filter": True,
        "max_iv_percentile": 80,
        "max_bid_ask_spread_pct": 5.0,
        "require_thesis_before_entry": True,
        "require_exit_plan_before_entry": True,
        "no_paris_warrants_at_european_open_after_us_earnings": True,
        "wait_until_1630_cet_after_us_earnings": True,
    },
    "position": {
        "max_single_position_pct": 10.0,
        "max_concurrent_leveraged": 3,
        "min_cash_reserve_pct": 20.0,
        "test_position_max_eur": 300,
        "min_portfolio_for_new_positions": 9000,
        "max_portfolio_correlation_to_single_sector": 0.6,
    },
    "exit": {
        "default_profit_target_pct": 25.0,
        "default_stop_loss_pct": 15.0,
        "time_stop_enabled": True,
        "trailing_stop_enabled": False,
        "trailing_stop_pct": 10.0,
    },
    "risk": {
        "max_daily_loss_eur": 500,
        "max_weekly_loss_eur": 1000,
        "max_binary_earnings_trades_per_week": 1,
        "blackout_hours_after_loss": 24,
        "no_revenge_trading": True,
        "no_chasing_5pct_plus_moves": True,
    },
    "psychological": {
        "log_emotional_state": True,
        "require_post_mortem": True,
        "panic_cooldown_hours": 2,
    },
}

# Human-readable checklist items derived from rules (for the UI compliance form)
RULE_CHECKLIST: list[dict] = [
    # Entry rules
    {"id": "entry_1", "category": "entry", "text": "News type is on the allowed list"},
    {"id": "entry_2", "category": "entry", "text": "Thesis is written BEFORE entry"},
    {"id": "entry_3", "category": "entry", "text": "Profit target AND stop loss are defined"},
    {"id": "entry_4", "category": "entry", "text": "IV percentile is below 80"},
    {"id": "entry_5", "category": "entry", "text": "Bid-ask spread < 5%"},
    {"id": "entry_6", "category": "entry", "text": "Market trend supports this trade"},
    {"id": "entry_7", "category": "entry", "text": "Sector trend supports this trade"},
    {"id": "entry_8", "category": "entry", "text": "Not chasing a 5%+ intraday move"},
    # Position rules
    {"id": "pos_1", "category": "position", "text": "Position size ≤ 10% of portfolio"},
    {"id": "pos_2", "category": "position", "text": "< 3 concurrent leveraged positions after this trade"},
    {"id": "pos_3", "category": "position", "text": "Cash reserve stays ≥ 20% after this trade"},
    {"id": "pos_4", "category": "position", "text": "No over-concentration in one sector (≤ 60%)"},
    # Risk rules
    {"id": "risk_1", "category": "risk", "text": "No loss in last 24 hours (blackout rule)"},
    {"id": "risk_2", "category": "risk", "text": "Daily loss < €500 today"},
    {"id": "risk_3", "category": "risk", "text": "Weekly loss < €1,000 this week"},
    {"id": "risk_4", "category": "risk", "text": "Not revenge trading after a loss"},
    # Psychological
    {"id": "psych_1", "category": "psychological", "text": "Emotional state is calm or confident"},
    {"id": "psych_2", "category": "psychological", "text": "Trade plan reviewed before entry"},
]
