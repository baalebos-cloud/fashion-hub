"""Every status update received from an external courier, once. The unique (courier, event_id)
pair makes webhook retries and reconciliation polls idempotent."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CourierEventRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "courier_events"
    __table_args__ = (UniqueConstraint("courier", "event_id", name="uq_courier_events_courier_event"),)

    courier: Mapped[str] = mapped_column(String(32), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    delivery_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("deliveries.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    applied: Mapped[str] = mapped_column(String(16), nullable=False)  # applied | ignored | unmatched
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
