"""One call between two parties on an order: a masked phone call, or an in-app call
(provider "livekit"). Phone numbers are never stored here."""
from datetime import datetime
import uuid

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CallSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "call_sessions"

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    caller_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    callee_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    callee_party: Mapped[str] = mapped_column(String(16), nullable=False)  # buyer | seller | rider
    provider: Mapped[str] = mapped_column(String(24), nullable=False)
    provider_session_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ringing_caller")
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # In-app calls: the private LiveKit room, and when the call was answered / ended.
    room_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

