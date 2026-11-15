"""A problem a buyer raises about a paid order (not delivered, wrong size, damaged...).

While a dispute is open the seller's payout for that order is held (payout_release_service.blocker).
An admin resolves it: a refund (through the normal refund service), a remake, or no action."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

DISPUTE_REASONS = ("not_delivered", "wrong_item", "wrong_size", "damaged", "poor_quality", "other")
DISPUTE_OUTCOMES = ("refund", "remake", "no_action")


class Dispute(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "disputes"
    __table_args__ = (
        # One open dispute per order at a time.
        Index("uq_disputes_one_open_per_order", "order_id", unique=True, postgresql_where=text("status = 'open'")),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"),
                                                nullable=False, index=True)
    opened_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", index=True)  # open | resolved
    outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)  # refund | remake | no_action
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    refund_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    refund_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
