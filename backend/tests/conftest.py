"""
Shared pytest fixtures.

Uses a real PostgreSQL test database (set TEST_DATABASE_URL) rather than
SQLite, because several models rely on PostgreSQL-specific types (UUID,
JSONB, ARRAY, PostGIS Geography) that SQLite cannot represent faithfully --
a passing test suite against SQLite would give false confidence.
"""
import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.constants import UserRole
from app.core.database import Base
from app.core.security import hash_password
from app.models.user import User

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://fashionhub:fashionhub@localhost:5432/fashionhub_test"
)


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def make_user(db):
    def _make_user(role: str = UserRole.CUSTOMER.value, **overrides) -> User:
        defaults = dict(
            email=f"{uuid.uuid4()}@example.com",
            hashed_password=hash_password("Password123"),
            full_name="Test User",
            role=role,
            is_active=True,
        )
        defaults.update(overrides)
        user = User(**defaults)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make_user
