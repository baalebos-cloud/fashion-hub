"""
Timezone helpers.

Rule: the backend ALWAYS generates and stores timestamps in UTC
(`utcnow()` below — never `datetime.now()` and never a client-supplied
timestamp). Conversion to the user's local timezone is a presentation
concern handled by the frontend/mobile client, or optionally by
`to_user_timezone` for server-rendered content (emails, PDFs).
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    """The single source of truth for 'now' across the entire backend.
    Never trust client-provided timestamps for business-critical events."""
    return datetime.now(timezone.utc)


def to_user_timezone(dt: datetime, tz_name: str = "UTC") -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        return dt.astimezone(ZoneInfo(tz_name))
    except Exception:
        return dt.astimezone(timezone.utc)
