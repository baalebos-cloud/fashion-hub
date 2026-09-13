"""User's saved/favorited professionals, designs, or vendor products."""
import uuid
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Favorite(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    favorite_type: Mapped[str] = mapped_column(String(32), nullable=False)  # professional | design | vendor_product
    favorite_ref_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
