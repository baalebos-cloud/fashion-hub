"""User-saved delivery addresses (a labeled pointer to a Location, e.g.
'Home', 'Office'), decoupled so one Location can't accidentally be edited by
two unrelated users."""
import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Address(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "addresses"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    label: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Home, Office, ...
    recipient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
