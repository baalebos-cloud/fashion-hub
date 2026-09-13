"""System notifications for push, SMS, or email dispatch trails."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notifications"

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(32), nullable=False)  # order_update | promotional | alert
    
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
