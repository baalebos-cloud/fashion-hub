"""Append-only log of every tracking/status ping for a delivery -- powers
the "delivery GPS stopped updating" alerting and historical route replay."""
import uuid
from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TrackingEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tracking_events"

    delivery_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # gps_ping | status_change | exception
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
