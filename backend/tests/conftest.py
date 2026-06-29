import os
from collections.abc import Generator

import pytest

os.environ["DATABASE_URL"] = "sqlite:///./akon_test.db"
os.environ["DEFAULT_AI_PROVIDER"] = "mock"
os.environ["SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes-long"
os.environ["AUTH_RATE_LIMIT_MAX_ATTEMPTS"] = "5"
os.environ["AUTH_RATE_LIMIT_WINDOW_SECONDS"] = "60"

from app.db.database import Base, engine
from app.models import AuditLog, Conversation, MemoryItem, Message, User  # noqa: F401
from app.services.rate_limit_service import reset_rate_limit_state


@pytest.fixture(autouse=True)
def reset_test_database() -> Generator[None, None, None]:
    """
    Reset the test database before and after every test.

    This keeps tests independent from each other and prevents the real local
    development database from affecting test results.
    """
    reset_rate_limit_state()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    reset_rate_limit_state()
    Base.metadata.drop_all(bind=engine)