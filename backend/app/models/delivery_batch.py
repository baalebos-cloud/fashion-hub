"""A rider's planned stop order across several deliveries (logistics phase 4).

The batch only *plans*: each order keeps its own Delivery, pickup and handover codes, events
and permissions. At most one active batch per rider.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DeliveryBatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "delivery_batches"
    __table_args__ = (
        Index("uq_delivery_batches_active_per_rider", "delivery_partner_id", unique=True,
              postgresql_where=text("status = 'active'")),
    )

    delivery_partner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("delivery_partners.id"),
                                                           nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")  # active | completed
    stops: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    total_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    baseline_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)  # one order at a time
    solver: Mapped[str | None] = mapped_column(String(16), nullable=True)
    matrix_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    planned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
