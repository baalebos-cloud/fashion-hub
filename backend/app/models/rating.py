"""Numeric rating attached to a review (kept separate to allow multi-axis
ratings later, e.g. quality/communication/timeliness, without migrating
Review)."""
import uuid
from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Rating(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ratings"

    review_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    axis: Mapped[str] = mapped_column(String(32), nullable=False, default="overall")
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
