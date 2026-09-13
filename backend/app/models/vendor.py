"""Verified material/fabric vendor business profile."""
import uuid
from sqlalchemy import Boolean, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Vendor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vendors"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    warehouse_location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    average_rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0, nullable=False)
