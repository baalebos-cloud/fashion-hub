"""
Customer -> Tailor/Designer review, and Tailor/Designer -> Vendor review.
`reviewer_user_id`/`reviewee_user_id` + `order_id` make reviews auditable
and tied to a completed transaction; review_service enforces that the
underlying order.status is RECEIVED/COMPLETED before allowing creation.
"""
import uuid
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Review(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "reviews"

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    reviewee_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
