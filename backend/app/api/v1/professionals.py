"""
/professionals

Public browse/search + the professional's own business-location update
(captured via the frontend's map picker, per the product requirement that
"business location should be picked from the map/GPS").
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_current_user
from app.core.exceptions import NotFoundError
from app.core.permissions import Role, require_roles
from app.models.professional import Professional
from app.models.user import User
from app.repositories.professional_repository import ProfessionalRepository
from app.schemas.professional import ProfessionalResponse
from app.services.professional_service import ProfessionalService

router = APIRouter(prefix="/professionals", tags=["Professionals"])


@router.get("", response_model=list[ProfessionalResponse])
def list_professionals(
    professional_type: str | None = Query(None),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    repo = ProfessionalRepository(db)
    return repo.list_verified(professional_type=professional_type, offset=pagination.offset, limit=pagination.page_size)


@router.get("/{professional_id}", response_model=ProfessionalResponse)
def get_professional(professional_id: UUID, db: Session = Depends(get_db)):
    professional = db.get(Professional, professional_id)
    if not professional:
        raise NotFoundError("Professional not found.")
    return professional


@router.patch("/me/location", response_model=ProfessionalResponse)
def update_my_business_location(
    latitude: float,
    longitude: float,
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
