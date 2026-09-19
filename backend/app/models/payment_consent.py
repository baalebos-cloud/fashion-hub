from datetime import datetime
from sqlalchemy.orm import Mapped
from typing import Any
"""
Digital consent record captured before/at checkout. This is an operational
audit record, NOT a verified legal e-signature -- do not represent it as one
without separately confirming applicable legal requirements.
"""
import uuid
from sqlalchemy import Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PaymentConsent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payment_consents"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    consent_text_version: Mapped[str] = mapped_column(String(32), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=False)
