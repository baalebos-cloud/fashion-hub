"""Shopping activity used to learn recommendations: what people view, add to cart, save,
search for, book and buy.

Deliberately minimal: who (account or a random per-browser ID), what (event and item), where on
the site it happened, and when. Never an IP address, location, device fingerprint or message
content. Rows are deleted after INTERACTION_RETENTION_DAYS, and immediately for an account that
turns personalised recommendations off.
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

EVENT_TYPES = ("view", "add_to_cart", "favorite", "search", "booking_started", "purchase")
ITEM_TYPES = ("product", "design", "professional")


class InteractionEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interaction_events"
    __table_args__ = (
        CheckConstraint("user_id IS NOT NULL OR anonymous_id IS NOT NULL", name="ck_interaction_events_actor"),
        CheckConstraint("(event_type = 'search') = (item_id IS NULL)", name="ck_interaction_events_item"),
        UniqueConstraint("dedupe_key", name="uq_interaction_events_dedupe_key"),
        Index("ix_interaction_events_item", "item_type", "item_id"),
        Index("ix_interaction_events_user_time", "user_id", "occurred_at"),
        Index("ix_interaction_events_anon_time", "anonymous_id", "occurred_at"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    # Random ID the browser generates for signed-out visitors; not derived from anything about them.
    anonymous_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)
    item_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Search text only, lower-cased and trimmed to 100 characters.
    search_query: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Which page or list the event came from (e.g. product_page, search_results, backfill).
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    # Makes the history backfill safe to re-run.
    dedupe_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
