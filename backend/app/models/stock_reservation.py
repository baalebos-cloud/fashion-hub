"""Durable stock allocation; terminal rows are retained as idempotency history."""
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class StockReservation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = 'stock_reservations'
    __table_args__ = (
        UniqueConstraint('order_id', 'product_variant_id', name='uq_reservation_order_variant'),
        CheckConstraint('quantity > 0', name='ck_reservation_quantity'),
        CheckConstraint("status IN ('active','consumed','released')", name='ck_reservation_status'),
    )
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orders.id'), nullable=False, index=True)
    product_variant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('product_variants.id'), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default='active')
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
