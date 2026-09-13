"""Individual line item inside a cart."""
import uuid
from sqlalchemy import Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CartItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cart_items"

    cart_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    product_variant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price_snapshot: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
