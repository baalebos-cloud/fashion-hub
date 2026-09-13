"""Identity verifications for users (Know Your Customer)."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class KYCVerification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "kyc_verifications"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    id_type: Mapped[str] = mapped_column(String(64), nullable=False)  # passport | national_id | drivers_license
    id_number: Mapped[str] = mapped_column(String(128), nullable=False)
    document_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
