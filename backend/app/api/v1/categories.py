"""Public design categories and admin-only category management."""
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ConflictError
from app.core.permissions import Role, require_roles
from app.models.category import Category
from app.models.user import User

router = APIRouter(prefix="/categories", tags=["Categories"])


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    slug: str


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=128)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=2, max_length=128)


@router.get("", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name, Category.id).all()


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(payload: CategoryCreate,
                    admin: User = Depends(require_roles(Role.ADMIN)),
                    db: Session = Depends(get_db)):
    if db.query(Category.id).filter(or_(Category.name == payload.name, Category.slug == payload.slug)).first():
        raise ConflictError("Category name or slug already exists.")
    item = Category(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Category name or slug already exists.") from None
    db.refresh(item)
    return item
