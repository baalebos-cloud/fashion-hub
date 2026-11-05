"""Shareable storefront handle: tailora.app/s/<handle> -> one shop's catalogue.

One namespace across tailors, designers and vendors, enforced by the unique
index on ``handle``; each account owns at most one handle.
"""
import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class StorefrontHandle(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "storefront_handles"

    handle: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    owner_type: Mapped[str] = mapped_column(String(16), nullable=False)  # professional | vendor
