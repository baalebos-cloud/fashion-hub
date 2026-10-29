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
from app.core.config import settings
from app.models.stored_media import StoredMedia
from app.models.design_image import DesignImage
from app.core.exceptions import ValidationAppError
from urllib.parse import urlsplit
import uuid
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

    image = None
    if payload.image_url:
        parsed = urlsplit(payload.image_url)
        expected = urlsplit(settings.APP_URL)
        if (parsed.scheme != expected.scheme or parsed.netloc != expected.netloc
                or not parsed.path.startswith(f"{settings.API_PREFIX}/media/files/")):
            raise ValidationAppError("Upload a design photo using the official media uploader.")
        try:
            media_id = uuid.UUID(parsed.path.rsplit("/", 1)[-1])
        except ValueError as exc:
            raise ValidationAppError("Invalid design photo reference.") from exc
        image = db.get(StoredMedia, media_id)
        if (not image or image.owner_user_id != current_user.id or not image.is_public
                or not image.storage_key.startswith("design/")):
            raise ValidationAppError("Design photo does not belong to this account.")
    service = DesignService(db)
    design = service.create_design(
        professional_id=professional.id,
        title=payload.title,
        description=payload.description,
        base_price=payload.base_price,
        category_id=payload.category_id,
        required_measurement_fields=payload.required_measurement_fields,
    )
    if image:
        db.add(DesignImage(design_id=design.id, professional_id=professional.id, image_url=payload.image_url))
        db.commit()
    return DesignResponse.model_validate(design).model_copy(update={"image_url": payload.image_url})
