"""Physical address geocoding coordinate points using GeoAlchemy."""
import uuid
from typing import Any
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geography

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Location(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "locations"

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line: Mapped[str] = mapped_column(String(512), nullable=False)
    city: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(128), nullable=False)
    country: Mapped[str] = mapped_column(String(128), default="Nigeria", nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)

    geom: Mapped[Any] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
