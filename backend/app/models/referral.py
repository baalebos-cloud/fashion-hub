from datetime import datetime
from sqlalchemy.orm import Mapped
from typing import Any
"""
Tracks a referral from signup through commission payout.

A Referral row is created the moment someone signs up using another
user's referral_code (see auth_service.py::sign_up). It only becomes
commission-worthy once the REFERRED person completes their first
successful PAID order (see referral_service.py::qualify_if_applicable,
called from payment_service.py on payment confirmation) -- signing up
alone earns nothing, by design, to prevent fake-signup abuse.
"""
import uuid
from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Referral(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "referrals"

    referrer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    referred_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    referral_code_used: Mapped[str] = mapped_column(String(16), nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)

    # Set once the referred person's first order is paid.
    qualifying_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    qualified_at: Mapped[datetime | None] = mapped_column(nullable=True)

    commission_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    commission_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)
