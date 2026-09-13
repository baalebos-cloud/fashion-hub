"""Measurement profile + field CRUD for customers."""
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError


class MeasurementService:
    def __init__(self, db: Session):
        self.db = db

    def create_profile(self, *, customer_id, label: str, garment_type: str | None, fields: list[dict]):
        from app.models.measurement import Measurement
        from app.models.measurement_profile import MeasurementProfile

        profile = MeasurementProfile(customer_id=customer_id, label=label, garment_type=garment_type)
        self.db.add(profile)
        self.db.flush()

        for field in fields:
            self.db.add(
                Measurement(
                    measurement_profile_id=profile.id,
                    field_name=field["field_name"],
                    value=field["value"],
                    unit=field.get("unit", "cm"),
                )
            )
        self.db.commit()
        self.db.refresh(profile)
        return profile
