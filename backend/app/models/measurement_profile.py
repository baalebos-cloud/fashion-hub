"""A named set of measurements a customer can reuse/select across orders
(e.g. 'My measurements', 'Son's measurements')."""
import uuid
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MeasurementProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "measurement_profiles"

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    garment_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
