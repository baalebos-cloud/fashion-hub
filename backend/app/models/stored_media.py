"""PostgreSQL bytea-backed uploads for installations without object storage."""
from sqlalchemy import Column, DateTime, ForeignKey, LargeBinary, String, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class StoredMedia(Base):
    __tablename__ = "stored_media"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True)
    owner_user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
