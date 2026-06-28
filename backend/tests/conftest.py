import os
from collections.abc import Generator

import pytest

os.environ["DATABASE_URL"] = "sqlite:///./akon_test.db"
os.environ["DEFAULT_AI_PROVIDER"] = "mock"

from app.db.database import Base, engine
from app.models import AuditLog, Conversation, MemoryItem, Message  # noqa: F401


@pytest.fixture(autouse=True)
def reset_test_database() -> Generator[None, None, None]:
    """
    Reset the test database before and after every test.

    This keeps tests independent from each other and prevents the real local
    development database from affecting test results.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)