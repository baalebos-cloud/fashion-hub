"""
Stock tracking per product variant. Row-level locking (SELECT ... FOR UPDATE)
is used in inventory_service when decrementing stock during checkout to
prevent overselling under concurrent requests.
"""
import uuid
from sqlalchemy import Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Inventory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "inventory"

    product_variant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    quantity_available: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
