"""A rider's fare offer on an open delivery request (InDrive-style bidding)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DeliveryOffer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "delivery_offers"
    __table_args__ = (UniqueConstraint("delivery_request_id", "delivery_partner_id",
                                       name="uq_delivery_offers_request_partner"),)

    delivery_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    delivery_partner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    eta_to_pickup_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    # pending | accepted | declined | withdrawn
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
