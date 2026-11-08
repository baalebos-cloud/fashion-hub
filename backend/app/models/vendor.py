from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from typing import Any
"""Verified material/fabric vendor business profile."""
import uuid
from sqlalchemy import Boolean, CheckConstraint, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Vendor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vendors"
    __table_args__ = (
        CheckConstraint("low_stock_threshold >= 0 AND low_stock_threshold <= 1000000", name="ck_vendors_low_stock_threshold_range"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False, index=True)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    warehouse_location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Stock at or below this many units counts as low on the vendor's pages. Vendor-chosen.
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10, server_default="10", nullable=False)
    average_rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0, nullable=False)
