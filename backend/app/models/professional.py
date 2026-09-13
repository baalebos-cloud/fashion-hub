"""
Shared professional profile fields for both tailors and designers.
`tailor.py` / `designer.py` extend this with a 1:1 link so tailor- and
designer-specific attributes (e.g. specialties, style tags) don't bloat a
single table, while shared fields (bio, years of experience, verification
badge) live once here.
"""
import uuid
from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Professional(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "professionals"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    professional_type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'tailor' | 'designer'

    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)

    shop_photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    average_rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    accepts_new_orders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
