"""
Append-only audit trail of every status transition an order goes through.
Never updated or deleted -- this is what powers the customer-facing order
tracker UI and disputes/support investigations.
"""
import uuid
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OrderTimelineEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "order_timeline"

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
