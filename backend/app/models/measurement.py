"""Individual body measurement values within a measurement profile."""
import uuid
from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Measurement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "measurements"

    measurement_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)  # chest, waist, sleeve_length, ...
    value: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(8), nullable=False, default="cm")
