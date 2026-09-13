"""
Core identity model. A single `users` table backs every persona
(customer, tailor, designer, vendor, delivery partner, admin); role-specific
profile data lives in dedicated tables (customer.py, tailor.py, vendor.py,
delivery_partner.py) linked 1:1 back to User. This avoids duplicating auth
concerns (password, sessions, verification) per role.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.constants import UserRole
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=UserRole.CUSTOMER.value)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile_photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role}>"


class RefreshSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Stored refresh tokens (hashed) so they can be individually revoked
    (e.g. 'log out of all devices') rather than only relying on JWT expiry."""
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


