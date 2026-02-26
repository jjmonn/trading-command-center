"""
Shared fixtures: in-memory SQLite database for fast, isolated tests.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import trades as _trade_models  # noqa: F401
from app.models import social as _social_models  # noqa: F401


@pytest.fixture()
def db():
    """Create an in-memory SQLite database and return a session."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
