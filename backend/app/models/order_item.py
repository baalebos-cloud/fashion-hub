"""Line items belonging to an order (design/service for customer orders,
product variants for vendor orders)."""
import uuid
from sqlalchemy import Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OrderItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    reference_type: Mapped[str] = mapped_column(String(32), nullable=False)  # design | service | product_variant
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    description_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
