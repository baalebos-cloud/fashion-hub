"""Vendor product categories (fabrics, buttons, zippers, threads, etc.)."""
import uuid
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class VendorCategory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vendor_categories"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    parent_category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
