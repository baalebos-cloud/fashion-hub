"""
High-level payment record tied 1:1 (usually) to an order. `payment_transactions`
stores the raw provider events (which can be many-to-one, e.g. retries) so
this table always reflects the current authoritative status while the
transaction log preserves full provider history for reconciliation/audit.
"""
import uuid
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payments"

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # paystack | flutterwave | ...
    provider_reference: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN")
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

