from datetime import datetime
from sqlalchemy.orm import Mapped
from typing import Any
"""Business (KYB) verification for vendors and professional businesses."""
import uuid
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class KYBVerification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "kyb_verifications"

    business_owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    business_registration_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    company_type: Mapped[str | None] = mapped_column(String(4), nullable=True)  # RC | BN | IT
    # Filled only from the CAC registry lookup, never from user input.
    verified_company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_match: Mapped[bool | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
