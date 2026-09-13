"""
A tailor/designer's shopping cart for purchasing vendor materials.
One active cart per (professional, vendor) pair is typical, but the model
allows a single cart to reference multiple vendors' items via cart_items;
checkout_service groups line items by vendor to produce one or more
vendor orders while still charging the buyer once (see checkout.py schema).
"""
import uuid
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Cart(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "carts"

    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)  # active|checked_out|abandoned
