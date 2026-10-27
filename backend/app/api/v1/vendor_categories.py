"""Public material categories and admin-only category management."""
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ConflictError, ValidationAppError
from app.core.permissions import Role, require_roles
from app.models.vendor_category import VendorCategory
from app.models.user import User

router = APIRouter(prefix="/vendor-categories", tags=["Vendor Categories"])


class VendorCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    slug: str
    parent_category_id: UUID | None


class VendorCategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=128)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=2, max_length=128)
    parent_category_id: UUID | None = None


@router.get("", response_model=list[VendorCategoryResponse])
def list_vendor_categories(db: Session = Depends(get_db)):
    return db.query(VendorCategory).order_by(VendorCategory.name, VendorCategory.id).all()


@router.post("", response_model=VendorCategoryResponse, status_code=201)
def create_vendor_category(payload: VendorCategoryCreate,
                           admin: User = Depends(require_roles(Role.ADMIN)),
                           db: Session = Depends(get_db)):
    if payload.parent_category_id is not None and db.get(VendorCategory, payload.parent_category_id) is None:
        raise ValidationAppError("Parent vendor category does not exist.")
    if db.query(VendorCategory.id).filter(or_(
        VendorCategory.name == payload.name, VendorCategory.slug == payload.slug,
    )).first():
        raise ConflictError("Vendor category name or slug already exists.")
    item = VendorCategory(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Vendor category name or slug already exists.") from None
    db.refresh(item)
    return item
