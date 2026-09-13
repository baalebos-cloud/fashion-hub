"""Delivery state tracker linked to a delivery request and order."""
import uuid
from datetime import datetime
from sqlalchemy import Numeric, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Delivery(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "deliveries"

    delivery_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    delivery_partner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    provider_tracking_reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    delivery_fee: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    estimated_arrival_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    proof_of_delivery_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
