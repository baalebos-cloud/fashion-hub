"""Admin access is limited to the emails in ADMIN_EMAILS.

In development and tests an empty list allows any admin account (so local tooling works);
in staging and production an empty list allows nobody, so a missing setting fails closed.
"""
from app.core.config import settings


def admin_email_allowed(email: str | None) -> bool:
    allowed = settings.ADMIN_EMAILS
    if not allowed:
        return settings.APP_ENV in {"development", "test"}
    return bool(email) and email.strip().lower() in allowed
