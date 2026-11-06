"""Who did what, from where: sign-ins (including failures) and every change made through the API.

Kept for ACTIVITY_LOG_RETENTION_DAYS, readable only by the admin. Stores the client IP,
browser/device description and a per-browser device ID. Never request bodies, passwords,
codes or tokens.
"""
import uuid

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ActivityLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "activity_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # sign_in | sign_in_failed | sign_up | sign_out | password_reset | admin_sign_in | admin_sign_in_failed | request
    event: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    method: Mapped[str | None] = mapped_column(String(8), nullable=True)
    path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AdminCredential(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """The admin's authenticator-app secret (Fernet-encrypted) and the last code step used."""
    __tablename__ = "admin_credentials"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    totp_secret_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    totp_enabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    totp_last_counter: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
