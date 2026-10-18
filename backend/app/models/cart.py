from sqlalchemy.orm import Mapped
from typing import Any
"""
A tailor/designer's shopping cart for purchasing vendor materials.
One active cart per (professional, vendor) pair is typical, but the model
allows a single cart to reference multiple vendors' items via cart_items;
checkout_service groups line items by vendor to produce one or more
vendor orders while still charging the buyer once (see checkout.py schema).
"""
import uuid
from sqlalchemy import CheckConstraint, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Cart(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "carts"
    __table_args__ = (
        Index("uq_cart_active_owner", "owner_user_id", unique=True, postgresql_where=text("status = 'active'")),
        CheckConstraint("revision >= 0", name="ck_cart_revision"),
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)  # active|checked_out|abandoned
