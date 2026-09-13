"""
Generated automatically after successful payment (see workers/invoice_tasks.py).
Contains a full line-item snapshot so historical invoices remain accurate
even if product prices change later.
"""
import uuid
from datetime import datetime
from sqlalchemy import Numeric, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Invoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "invoices"

    invoice_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    issued_to_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    issued_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    line_items_snapshot: Mapped[list] = mapped_column(JSONB, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_fee: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN")

    payment_status: Mapped[str] = mapped_column(String(16), nullable=False)
    payment_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    payment_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

