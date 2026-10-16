"""Authenticated customer-owned measurement profiles."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.models.customer import Customer
from app.models.measurement import Measurement
from app.models.measurement_profile import MeasurementProfile
from app.models.user import User
from app.schemas.measurement import CreateMeasurementProfileRequest, MeasurementProfileResponse

router = APIRouter(prefix='/measurements', tags=['Measurements'])


def serialize(profile, fields):
    return MeasurementProfileResponse(id=profile.id, label=profile.label, garment_type=profile.garment_type, fields=fields)


@router.get('', response_model=list[MeasurementProfileResponse])
def list_profiles(user: User = Depends(require_roles(Role.CUSTOMER)), db: Session = Depends(get_db)):
    profiles = (db.query(MeasurementProfile).join(Customer, Customer.id == MeasurementProfile.customer_id)
                .filter(Customer.user_id == user.id).order_by(MeasurementProfile.created_at.desc()).limit(100).all())
    fields = db.query(Measurement).filter(Measurement.measurement_profile_id.in_([p.id for p in profiles])).all() if profiles else []
    grouped = {}
    for field in fields:
        grouped.setdefault(field.measurement_profile_id, []).append(field)
    return [serialize(p, grouped.get(p.id, [])) for p in profiles]


@router.post('', response_model=MeasurementProfileResponse, status_code=201)
def create_profile(payload: CreateMeasurementProfileRequest, user: User = Depends(require_roles(Role.CUSTOMER)), db: Session = Depends(get_db)):
    # Sign-up creates the account first. Lazily provision its customer profile
    # under an account lock so parallel profile saves cannot violate uniqueness.
    db.query(User).filter(User.id == user.id).with_for_update().one()
    customer = db.query(Customer).filter(Customer.user_id == user.id).first()
    if not customer:
        customer = Customer(user_id=user.id)
        db.add(customer)
        db.flush()
    profile = MeasurementProfile(customer_id=customer.id, label=payload.label, garment_type=payload.garment_type)
    db.add(profile)
    db.flush()
    fields = [Measurement(measurement_profile_id=profile.id, **f.model_dump()) for f in payload.fields]
    db.add_all(fields)
    db.commit()
    db.refresh(profile)
    return serialize(profile, fields)
