"""Delivery partner (rider/courier) profile."""
import uuid
from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DeliveryPartner(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "delivery_partners"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # bike | car | van | foot
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    average_rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0, nullable=False)
    current_location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
