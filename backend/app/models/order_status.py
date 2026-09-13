"""
Lookup/reference table describing valid statuses per order_type. Primarily
used to drive admin dashboards and API discovery (GET /orders/statuses)
rather than for runtime validation -- runtime validation uses the enums and
transition maps in app/core/constants.py, which are authoritative.
"""
from sqlalchemy import String

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy.orm import Mapped, mapped_column


class OrderStatusDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "order_status_definitions"

    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)
