"""
/professionals

Public browse/search + the professional's own business-location update
(captured via the frontend's map picker, per the product requirement that
"business location should be picked from the map/GPS").
"""
from uuid import UUID
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_current_user
from app.core.exceptions import NotFoundError
from app.core.permissions import Role, require_roles
from app.models.professional import Professional
from app.models.user import User
from app.repositories.professional_repository import ProfessionalRepository
from app.schemas.professional import ProfessionalResponse, ProfessionalPage, ProfessionalProfileRequest
from app.services.professional_service import ProfessionalService

router = APIRouter(prefix="/professionals", tags=["Professionals"])


@router.get("", response_model=ProfessionalPage)
def list_professionals(
    professional_type: Literal['tailor', 'designer'] | None = None,
    q: str | None = Query(None, max_length=200),
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    radius_km: float = Query(10, gt=0, le=200),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    if (lat is None) != (lng is None):
        from app.core.exceptions import ValidationAppError
        raise ValidationAppError('Provide both latitude and longitude.')
    query = ProfessionalRepository(db).verified_query(professional_type=professional_type,
        query=q, latitude=lat, longitude=lng, radius_km=radius_km)
    return {'items': query.order_by(Professional.id).offset(pagination.offset).limit(pagination.page_size).all(),
            'total': query.count(), 'page': pagination.page, 'page_size': pagination.page_size}


@router.get('/me', response_model=ProfessionalResponse | None)
def my_profile(user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER)), db: Session = Depends(get_db)):
    return db.query(Professional).filter_by(user_id=user.id).first()


@router.put('/me', response_model=ProfessionalResponse)
def save_profile(payload: ProfessionalProfileRequest,
                 user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER)), db: Session = Depends(get_db)):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    profile = db.query(Professional).filter_by(user_id=user.id).first()
    if profile is None:
        profile = Professional(user_id=user.id, professional_type=user.role, is_verified=False)
        db.add(profile)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.post('/{professional_id}/verify', response_model=ProfessionalResponse)
def verify_profile(professional_id: UUID, user: User = Depends(require_roles(Role.ADMIN)), db: Session = Depends(get_db)):
    from app.models.audit_log import AuditLog
    profile = db.query(Professional).filter_by(id=professional_id).with_for_update().first()
    if not profile:
        raise NotFoundError('Professional not found.')
    if not profile.is_verified:
        profile.is_verified = True
        db.add(AuditLog(actor_user_id=user.id, action='professional.verified', resource_type='professional', resource_id=profile.id))
        db.commit()
    return profile


@router.get("/{professional_id}", response_model=ProfessionalResponse)
def get_professional(professional_id: UUID, db: Session = Depends(get_db)):
    professional = db.get(Professional, professional_id)
    if not professional:
        raise NotFoundError("Professional not found.")
    return professional


@router.patch("/me/location", response_model=ProfessionalResponse)
def update_my_business_location(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    formatted_address: str | None = None,
    current_user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER)),
    db: Session = Depends(get_db),
):
    from app.models.location import Location

    professional = db.query(Professional).filter(Professional.user_id == current_user.id).first()
    if not professional:
        raise NotFoundError("Professional profile not found for this account.")

    location = Location(latitude=latitude, longitude=longitude, location_type="tailor_shop", formatted_address=formatted_address)
    db.add(location)
    db.flush()

    service = ProfessionalService(db)
    return service.update_profile(professional.id, actor_user_id=current_user.id, location_id=location.id)
