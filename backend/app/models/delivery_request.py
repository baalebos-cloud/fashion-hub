"""
A request to fulfill delivery for an order, created once an order reaches
READY_FOR_DELIVERY / READY_FOR_PICKUP. Separated from `Delivery` so a
request can be rejected/re-broadcast to another partner without losing the
audit trail of who rejected it and why.
"""
import uuid
from sqlalchemy import Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DeliveryRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "delivery_requests"

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    pickup_location_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dropoff_location_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    package_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_fee: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="requested", index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
