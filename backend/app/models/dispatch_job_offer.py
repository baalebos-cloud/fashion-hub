"""A platform-initiated, time-limited exclusive offer of one job to one rider.

Distinct from DeliveryOffer (a rider's own fare bid). At most one offer per job
can be live at a time (partial unique index), and a rider is offered a given
job at most once.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DispatchJobOffer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "dispatch_job_offers"
    __table_args__ = (
        UniqueConstraint("delivery_request_id", "delivery_partner_id", name="uq_job_offers_request_partner"),
        Index("uq_job_offers_one_live_per_request", "delivery_request_id", unique=True,
              postgresql_where=text("status = 'offered'")),
    )

    delivery_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_requests.id"), nullable=False, index=True)
    delivery_partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_partners.id"), nullable=False, index=True)
    # offered | accepted | declined | expired | withdrawn
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="offered", index=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    # Straight-line km from the rider's known base to pickup, used for ranking only.
    distance_km: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
