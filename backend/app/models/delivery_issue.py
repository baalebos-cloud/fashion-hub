"""Courier incident reports; a Sage-inspired local intake, not a Sage API bridge."""
import uuid
from sqlalchemy import ForeignKey, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

ISSUE_TYPES = {"CUSTOMER_UNREACHABLE", "WRONG_ADDRESS", "PACKAGE_DAMAGED", "TRAFFIC_ACCIDENT_DELAY", "RECIPIENT_REJECTED", "VEHICLE_BREAKDOWN"}

class DispatchIssueReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "dispatch_issue_reports"
    delivery_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deliveries.id"), nullable=False, index=True)
    courier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    issue_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    photo_evidence_url: Mapped[str | None] = mapped_column(String(1024))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="OPEN")
