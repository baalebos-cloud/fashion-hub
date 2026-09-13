"""
Customer clothing order AND vendor material order share this table via
`order_type` discriminator ('customer_order' | 'vendor_order') because both
need identical infrastructure: items, status machine, timeline, payment,
invoice, delivery link. Keeping them in one table simplifies invoicing and
audit queries; order_service enforces which status enum applies per type.
"""
import uuid
from datetime import datetime  # Added for type hints
from sqlalchemy import Numeric, String, DateTime  # Added DateTime core type
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Order(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)  # customer_order | vendor_order

    buyer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    seller_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    delivery_fee: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="NGN", nullable=False)

    delivery_address_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    measurement_profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Server-controlled lifecycle timestamps. Never populated from client input.
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    production_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    out_for_delivery_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Idempotency guard for duplicate order submission from flaky clients.
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)

