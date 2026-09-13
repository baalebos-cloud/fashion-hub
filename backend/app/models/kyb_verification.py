"""Vendor business verifications (Know Your Business)."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class KYBVerification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "kyb_verifications"

    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    business_registration_number: Mapped[str] = mapped_column(String(128), nullable=False)
    document_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
