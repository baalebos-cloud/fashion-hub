"""AI assistant conversation thread, scoped to a single user (the assistant
never mixes context across users -- see ai_service.py)."""
import uuid
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AIConversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
