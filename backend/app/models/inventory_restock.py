"""Append-only restock intent; retained to deduplicate lost-response retries."""
import uuid
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class InventoryRestock(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'inventory_restocks'
    __table_args__ = (CheckConstraint('quantity > 0 AND quantity <= 1000000000', name='ck_restock_quantity'),)
    product_variant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('product_variants.id'), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
