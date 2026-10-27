"""Owned favorites, restricted to published and verified catalog entries."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.models.design import Design
from app.models.favorite import Favorite
from app.models.professional import Professional
from app.models.user import User
from app.models.vendor import Vendor
from app.models.vendor_product import VendorProduct
from app.services.favorite_service import FavoriteService

router = APIRouter(prefix="/favorites", tags=["Favorites"])
FavoriteType = Literal["professional", "design", "vendor_product"]


class FavoriteRequest(BaseModel):
    favorite_type: FavoriteType
    favorite_ref_id: UUID


def _check_visible(db: Session, kind: FavoriteType, ref_id: UUID) -> None:
    if kind == "professional":
        result = (db.query(Professional.id).join(User, User.id == Professional.user_id)
                  .filter(Professional.id == ref_id, Professional.is_verified.is_(True),
                          User.is_active.is_(True)).first())
    elif kind == "design":
        result = (db.query(Design.id)
                  .join(Professional, Professional.id == Design.professional_id)
                  .join(User, User.id == Professional.user_id)
                  .filter(Design.id == ref_id, Design.is_published.is_(True),
                          Professional.is_verified.is_(True), User.is_active.is_(True)).first())
    else:
        result = (db.query(VendorProduct.id)
                  .join(Vendor, Vendor.id == VendorProduct.vendor_id)
                  .join(User, User.id == Vendor.user_id)
                  .filter(VendorProduct.id == ref_id, VendorProduct.is_active.is_(True),
                          Vendor.is_verified.is_(True), User.is_active.is_(True),
                          User.role == "vendor").first())
    if not result:
        raise NotFoundError("Listing not found.")


@router.get("")
def list_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(Favorite).filter(Favorite.user_id == user.id)
            .order_by(Favorite.created_at.desc(), Favorite.id).limit(100).all())
    return [{"id": row.id, "favorite_type": row.favorite_type,
             "favorite_ref_id": row.favorite_ref_id} for row in rows]


@router.post("")
def toggle_favorite(payload: FavoriteRequest, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    _check_visible(db, payload.favorite_type, payload.favorite_ref_id)
    return {"favorited": FavoriteService(db).toggle_favorite(
        user_id=user.id, favorite_type=payload.favorite_type, favorite_ref_id=payload.favorite_ref_id,
    )}
