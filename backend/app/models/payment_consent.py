"""Pre-authorization or card saving consents for milestones."""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PaymentConsent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payment_consents"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    gateway_customer_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    gateway_token_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    card_brand: Mapped[str | None] = mapped_column(String(32), nullable=True)
    card_last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
