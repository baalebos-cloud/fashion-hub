"""Formatting helpers for presenting server-stored UTC timestamps."""
from datetime import datetime

from app.core.timezone import to_user_timezone


def format_for_display(dt: datetime, tz_name: str = "UTC") -> str:
    local = to_user_timezone(dt, tz_name)
    return local.strftime("%Y-%m-%d %H:%M:%S %Z")
