"""Role-owned customer profile, including an optional owned measurement default."""
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenError
from app.core.permissions import Role, require_roles
from app.models.customer import Customer
from app.models.measurement_profile import MeasurementProfile
from app.models.user import User
from app.schemas.customer import CustomerResponse

router = APIRouter(prefix="/customers", tags=["Customers"])


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_measurement_profile_id: UUID | None = None


def _profile(db: Session, user: User) -> Customer:
    # Lock the identity row so concurrent first requests create only one profile.
    db.query(User).filter(User.id == user.id).with_for_update().one()
    profile = db.query(Customer).filter_by(user_id=user.id).first()
    if profile is None:
        profile = Customer(user_id=user.id, preferred_currency="NGN")
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("/me", response_model=CustomerResponse)
def my_customer_profile(user: User = Depends(require_roles(Role.CUSTOMER)),
                        db: Session = Depends(get_db)):
    return _profile(db, user)


@router.patch("/me", response_model=CustomerResponse)
def update_customer_profile(payload: CustomerUpdate,
                            user: User = Depends(require_roles(Role.CUSTOMER)),
                            db: Session = Depends(get_db)):
    profile = _profile(db, user)
    if "default_measurement_profile_id" in payload.model_fields_set:
        if payload.default_measurement_profile_id is not None:
            owned = (db.query(MeasurementProfile.id).filter(
                MeasurementProfile.id == payload.default_measurement_profile_id,
                MeasurementProfile.customer_id == profile.id,
            ).first())
            if not owned:
                raise ForbiddenError("Only an owned measurement profile can be selected.")
        profile.default_measurement_profile_id = payload.default_measurement_profile_id
        db.commit()
        db.refresh(profile)
    return profile
