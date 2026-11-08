"""One ranked list shown to one shopper, for measuring rules vs learned ranking.

Records which surface, which ranking (variant), who (account or browser ID) and the items shown,
in order. Clicks and purchases are not stored here: they're the shopper's own activity in
interaction_events, matched to impressions when the admin report is built. Same retention and
opt-out deletion as shopping activity; never stores IP or location.
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

SURFACES = ("budget_guide", "picked_for_you", "tailor_search")
VARIANTS = ("rules", "learned")


class RecommendationImpression(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "recommendation_impressions"
    __table_args__ = (
        CheckConstraint("user_id IS NOT NULL OR anonymous_id IS NOT NULL", name="ck_recommendation_impressions_actor"),
        Index("ix_recommendation_impressions_surface_time", "surface", "served_at"),
        Index("ix_recommendation_impressions_user", "user_id"),
    )

    surface: Mapped[str] = mapped_column(String(24), nullable=False)
    variant: Mapped[str] = mapped_column(String(16), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    anonymous_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    item_type: Mapped[str] = mapped_column(String(16), nullable=False)
    item_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    served_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
