"""
/designs

Public browse + the owning professional's create/update. Each design can
declare its own required_measurement_fields (see schemas/design.py) --
this is what the frontend's CreateOrder flow reads to decide which
measurement fields to require versus letting the customer's own saved
profile stand as-is.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.models.professional import Professional
from app.models.user import User
from app.repositories.design_repository import DesignRepository
from app.schemas.design import CreateDesignRequest, DesignResponse
from app.services.design_service import DesignService

router = APIRouter(prefix="/designs", tags=["Designs"])


@router.get("", response_model=list[DesignResponse])
def list_designs(professional_id: UUID | None = Query(None), db: Session = Depends(get_db)):
    if not professional_id:
        return []
    return DesignRepository(db).list_for_professional(professional_id)


@router.post("", response_model=DesignResponse, status_code=201)
def create_design(
    payload: CreateDesignRequest,
    current_user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER)),
    db: Session = Depends(get_db),
):
    from app.core.exceptions import NotFoundError

    professional = db.query(Professional).filter(Professional.user_id == current_user.id).first()
    if not professional:
        raise NotFoundError("Professional profile not found for this account.")

    service = DesignService(db)
    return service.create_design(
        professional_id=professional.id,
        title=payload.title,
        description=payload.description,
        base_price=payload.base_price,
        category_id=payload.category_id,
        required_measurement_fields=payload.required_measurement_fields,
    )
