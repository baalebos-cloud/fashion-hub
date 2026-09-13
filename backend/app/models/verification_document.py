"""
Uploaded supporting documents for KYC/KYB (ID photos, business certificates).
Stored privately via the storage integration -- URLs here are pre-signed/
proxy URLs, never public, and access is restricted to the owner + admins
(see kyc_service.get_document_url).
"""
import uuid
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class VerificationDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "verification_documents"

    kyc_verification_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    kyb_verification_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
