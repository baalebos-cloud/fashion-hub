"""Realtime location coordinate snapshot data for dynamic maps."""
import uuid
from datetime import datetime
from sqlalchemy import Numeric, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DeliveryTracking(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "delivery_tracking"

    delivery_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    current_latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    current_longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    current_status: Mapped[str] = mapped_column(String(24), nullable=False)
    last_ping_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
