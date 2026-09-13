"""Record of any concrete action the AI assistant suggested/performed
(navigation link, FAQ shown, etc.) -- kept for auditing what the assistant
told users, especially for reviewing wrong-navigation incidents."""
import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AIAction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_actions"

    ai_message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)  # navigate | faq | escalate
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    was_helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # user feedback
