"""Tailor-specific extension of Professional (garment categories, pricing model)."""
import uuid
from sqlalchemy import ARRAY, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Tailor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tailors"

    professional_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    garment_specialties: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    turnaround_time_days: Mapped[int | None] = mapped_column(nullable=True)
