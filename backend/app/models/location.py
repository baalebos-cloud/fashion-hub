from sqlalchemy.orm import Mapped
from typing import Any
"""
Geospatial location using PostGIS's Geography type for accurate
distance/nearby queries (e.g. "tailors within 5km"). Precise coordinates
are restricted in schemas/services to users who need them for fulfillment
(see location_service.get_public_location which truncates precision).
"""
import uuid
from geoalchemy2 import Geography
from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Location(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "locations"

    latitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    # Generated/populated alongside lat/lon for ST_DWithin / KNN queries.
    geom: Mapped[Any] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)

    location_type: Mapped[str] = mapped_column(String(32), nullable=False)
    formatted_address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state_region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
