"""A design/service offered by a tailor or designer that customers can order."""
import uuid
from sqlalchemy import Boolean, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Design(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "designs"

    professional_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="NGN", nullable=False)
    estimated_turnaround_days: Mapped[int | None] = mapped_column(nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
