"""Customer profile: 1:1 extension of User for shoppers ordering clothing."""
import uuid
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Customer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "customers"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    default_measurement_profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    preferred_currency: Mapped[str] = mapped_column(String(8), default="NGN", nullable=False)
