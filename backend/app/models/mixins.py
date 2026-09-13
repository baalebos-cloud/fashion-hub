"""
Reusable model mixins so every table gets consistent, server-generated
timestamps and UUID primary keys without repeating boilerplate.
"""
import uuid

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """created_at/updated_at are ALWAYS set by the database server
    (func.now()), never by application code, so clock skew or a malicious
    client can't forge history."""

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
