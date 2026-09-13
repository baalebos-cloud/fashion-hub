"""Portfolio/design gallery images."""
import uuid
from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DesignImage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "design_images"

    design_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    professional_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    image_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
