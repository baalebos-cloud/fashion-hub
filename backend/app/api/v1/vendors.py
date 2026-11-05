"""Owned vendor profiles; only administrators can grant verification."""
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.core.exceptions import ConflictError, NotFoundError
from app.models.user import User
from app.models.vendor import Vendor
from app.models.audit_log import AuditLog
from app.schemas.vendor import VendorCreateRequest, VendorResponse

router = APIRouter(prefix='/vendors', tags=['Vendors'])


@router.get('/me', response_model=VendorResponse | None)
def mine(user: User = Depends(require_roles(Role.VENDOR)), db: Session = Depends(get_db)):
    return db.query(Vendor).filter_by(user_id=user.id).first()


@router.post('/me', response_model=VendorResponse, status_code=201)
def create(payload: VendorCreateRequest, user: User = Depends(require_roles(Role.VENDOR)), db: Session = Depends(get_db)):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    if db.query(Vendor).filter_by(user_id=user.id).first():
        raise ConflictError('A vendor profile already exists.')
    profile = Vendor(user_id=user.id, **payload.model_dump(), is_verified=False)
    db.add(profile)
    db.commit()
    return profile


@router.patch('/me/location', response_model=VendorResponse)
def set_pickup_location(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    formatted_address: str | None = Query(None, max_length=512),
    city: str | None = Query(None, max_length=128),
    state_region: str | None = Query(None, max_length=128),
    country: str | None = Query(None, max_length=128),
    user: User = Depends(require_roles(Role.VENDOR)),
    db: Session = Depends(get_db),
):
    """Store pickup point riders collect materials from. Each save creates a new Location,
    so deliveries already dispatched keep their own pickup snapshot."""
    from app.models.location import Location
    from app.services.location_service import point_geography

    def clean(value: str | None) -> str | None:
        return value.strip() or None if value else None

    profile = db.query(Vendor).filter_by(user_id=user.id).first()
    if not profile:
        raise NotFoundError('Create your vendor store first.')
    location = Location(latitude=latitude, longitude=longitude, geom=point_geography(latitude, longitude),
                        location_type='vendor_warehouse',
                        formatted_address=clean(formatted_address), city=clean(city),
                        state_region=clean(state_region), country=clean(country))
    db.add(location)
    db.flush()
    profile.warehouse_location_id = location.id
    db.commit()
    db.refresh(profile)
    return profile


@router.post('/{vendor_id}/verify', response_model=VendorResponse)
def verify(vendor_id: uuid.UUID, user: User = Depends(require_roles(Role.ADMIN)), db: Session = Depends(get_db)):
    profile = db.query(Vendor).filter_by(id=vendor_id).with_for_update().populate_existing().first()
    if not profile:
        raise NotFoundError('Vendor not found.')
    if not profile.is_verified:
        profile.is_verified = True
        db.add(AuditLog(actor_user_id=user.id, action='vendor.verified', resource_type='vendor', resource_id=profile.id))
        db.commit()
    return profile
