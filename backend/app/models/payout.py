from datetime import datetime
from sqlalchemy.orm import Mapped
from typing import Any
"""
Records what a professional/vendor actually nets on an order after the
platform commission -- see docs/commission.md. Created once, when a
payment for the order is confirmed (see payment_service.py).

CRITICAL: gross_amount / commission_amount / commission_rate are seller-
facing figures only. The customer's invoice (see invoice_service.py) is
built from Order.total_amount alone and never references this table --
the commission is invisible to the customer by construction, not by a
permission check that could be bypassed.
"""
import uuid
from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Payout(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payouts"

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    seller_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    gross_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    commission_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    net_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN")

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending | released
    released_at: Mapped[datetime | None] = mapped_column(nullable=True)
