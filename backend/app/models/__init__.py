# Import all models so SQLAlchemy/Alembic sees them during metadata introspection.
from app.models.social import SocialSignal  # noqa: F401  (must be before Trade)
from app.models.trades import DailySnapshot, StrategyRules, Tag, Trade, trade_tags  # noqa: F401
from app.models.portfolio import PortfolioHistory, Position  # noqa: F401
from app.models.markets import AlignmentScore, FactorSnapshot, Watchlist  # noqa: F401
