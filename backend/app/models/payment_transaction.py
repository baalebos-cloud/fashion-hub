"""
Raw log of every payment-provider event received (webhook or verify-call),
including duplicates. `provider_event_id` has a unique constraint so the
SAME webhook delivered twice can never be double-processed -- this is the
database-level backstop behind the Redis idempotency lock in payment_service.
"""
import uuid
from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PaymentTransaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payment_transactions"

    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)  # charge.success, charge.failed, ...
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(nullable=False, default=False)
