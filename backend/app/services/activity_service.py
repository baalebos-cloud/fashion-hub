"""Record sign-ins and changes with IP, device and browser, for the admin's security view."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.client_info import client_ip, device_id, user_agent
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.core.timezone import utcnow
from app.models.activity_log import ActivityLog

logger = get_logger(__name__)


def build(request: Request, event: str, *, user=None, user_id=None, role=None, status_code=None,
          path=None, details: dict | None = None) -> ActivityLog:
    return ActivityLog(
        user_id=getattr(user, "id", None) or user_id, role=getattr(user, "role", None) or role,
        event=event, method=request.method, path=(path or request.url.path)[:255], status_code=status_code,
        ip_address=client_ip(request), user_agent=user_agent(request), device_id=device_id(request),
        details=details or None)


def _session(request: Request):
    """A session of its own (so the entry survives the caller's rollback), or the app's
    overridden session where tests replace get_db."""
    from app.core.database import get_db
    override = request.app.dependency_overrides.get(get_db)
    if override is not None:
        provided = override()
        if hasattr(provided, "__next__"):  # a generator-style override yields the session
            provided = next(provided)
        return provided, False
    return SessionLocal(), True


def record(request: Request, event: str, **kwargs) -> None:
    """Write one entry. Never raises: security logging must not break the request it describes."""
    db, owned = _session(request)
    try:
        db.add(build(request, event, **kwargs))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("activity_log_write_failed", extra={"event": event})
    finally:
        if owned:
            db.close()


def purge_expired(db: Session) -> int:
    cutoff = utcnow() - timedelta(days=settings.ACTIVITY_LOG_RETENTION_DAYS)
    deleted = db.query(ActivityLog).filter(ActivityLog.created_at < cutoff).delete(synchronize_session=False)
    db.commit()
    return deleted
