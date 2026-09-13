"""Fashion designer-specific extension of Professional (style focus, collections)."""
import uuid
from sqlalchemy import ARRAY, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Designer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "designers"

    professional_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    style_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    signature_collection: Mapped[str | None] = mapped_column(String(255), nullable=True)
