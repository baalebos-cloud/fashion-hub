"""Refund requests and their processing lifecycle."""
import uuid
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy import Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Refund(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "refunds"

    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="requested", index=True)
    provider_refund_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

