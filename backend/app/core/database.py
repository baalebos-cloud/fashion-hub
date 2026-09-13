"""
Database engine, session factory, and declarative base.

Design notes:
- One SQLAlchemy engine per process, pooled connections.
- `get_db` is a FastAPI dependency that yields a session and guarantees close().
- Repositories/services receive a Session via dependency injection; they never
  create their own engine or session, which keeps unit tests easy to isolate.
- PostGIS types (Geography/Geometry) are used on models that store
  coordinates (see app/models/location.py).
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager for use OUTSIDE the request lifecycle
    (Celery tasks, scripts, background jobs). Commits on success,
    rolls back on exception.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_health() -> bool:
    """Used by /health/ready. Runs a trivial query to confirm connectivity."""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
