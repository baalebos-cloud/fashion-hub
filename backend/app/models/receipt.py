"""Payment receipt issued to the payer once a payment clears (distinct from
the invoice, which itemizes goods/services; the receipt confirms payment)."""
import uuid
from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Receipt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "receipts"

    receipt_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN")
    pdf_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
