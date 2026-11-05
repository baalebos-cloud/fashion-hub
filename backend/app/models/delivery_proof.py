"""Phase 6 delivery proof: one-time pickup/handover codes and an append-only event log.

Codes are never stored in plaintext. Each row keeps a random nonce; the six-digit code is
HMAC(SECRET_KEY, purpose|delivery|nonce), so a database leak alone reveals nothing.
"""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DeliveryCode(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "delivery_codes"
    __table_args__ = (
        # At most one live code per delivery and purpose.
        Index("uq_delivery_codes_live", "delivery_id", "purpose", unique=True,
              postgresql_where=text("used_at IS NULL AND revoked_at IS NULL")),
    )

    delivery_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deliveries.id"), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)  # pickup | handover
    nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeliveryEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Append-only audit trail of what happened on a delivery run. Never holds codes or PII."""
    __tablename__ = "delivery_events"
    __table_args__ = (
        Index("uq_delivery_events_idempotency", "delivery_id", "idempotency_key", unique=True,
              postgresql_where=text("idempotency_key IS NOT NULL")),
    )

    # Strict append order (created_at ties within one transaction).
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False, unique=True)
    delivery_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deliveries.id"), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
