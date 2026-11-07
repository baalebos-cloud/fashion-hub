"""Learned "related items", rebuilt nightly from shopping activity (interaction_events).

signal = viewed_together: shoppers who engaged with item_id also engaged with related_id.
signal = bought_together: the same, counting only cart adds and purchases.
score is a 0-1 similarity; support is how many different shoppers produced the pair.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

SIGNALS = ("viewed_together", "bought_together")


class ItemSimilarity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "item_similarities"
    __table_args__ = (
        UniqueConstraint("item_type", "item_id", "signal", "related_id", name="uq_item_similarities_pair"),
        Index("ix_item_similarities_lookup", "item_type", "item_id", "signal"),
    )

    item_type: Mapped[str] = mapped_column(String(16), nullable=False)
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    related_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    signal: Mapped[str] = mapped_column(String(24), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    support: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
