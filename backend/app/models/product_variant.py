"""Purchasable variants of a vendor product (e.g. color/size/unit of a fabric)."""
import uuid
from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import UUID, JSONB  # Added JSONB for dict mapping
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ProductVariant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_variants"

    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Fixed: Explicitly mapped to JSONB column
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

