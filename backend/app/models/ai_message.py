"""Individual turn within an AI conversation."""
import uuid
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AIMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # e.g. {"navigate_to": "/orders/:id"}
