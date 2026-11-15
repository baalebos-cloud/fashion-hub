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


def _describe(db: Session, row: Favorite) -> dict:
    """Name, photo and price for the Favorites page. `available` is False when the listing is no
    longer shown publicly (unpublished, deactivated, unverified), so the page can say so."""
    try:
        _check_visible(db, row.favorite_type, row.favorite_ref_id)
        available = True
    except NotFoundError:
        available = False
    info = {"title": None, "subtitle": None, "image_url": None, "price": None, "currency": None, "professional_id": None}
    if row.favorite_type == "professional":
        pro = db.get(Professional, row.favorite_ref_id)
        if pro:
            info.update(title=pro.business_name, subtitle=pro.professional_type.title() if pro.professional_type else None,
                        image_url=pro.shop_photo_url, professional_id=str(pro.id))
    elif row.favorite_type == "design":
        design = db.get(Design, row.favorite_ref_id)
        if design:
            from app.models.design_image import DesignImage
            image = (db.query(DesignImage).filter(DesignImage.design_id == design.id)
                     .order_by(DesignImage.sort_order, DesignImage.created_at).first())
            pro = db.get(Professional, design.professional_id)
            info.update(title=design.title, subtitle=pro.business_name if pro else None,
                        image_url=image.image_url if image else None, price=float(design.base_price),
                        currency=design.currency, professional_id=str(design.professional_id))
    else:
        product = db.get(VendorProduct, row.favorite_ref_id)
        if product:
            vendor = db.get(Vendor, product.vendor_id)
            info.update(title=product.name, subtitle=vendor.business_name if vendor else None,
                        image_url=product.primary_image_url, price=float(product.base_price), currency=product.currency)
    return {**info, "available": available and info["title"] is not None}


@router.get("")
def list_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(Favorite).filter(Favorite.user_id == user.id)
            .order_by(Favorite.created_at.desc(), Favorite.id).limit(100).all())
    return [{"id": row.id, "favorite_type": row.favorite_type, "favorite_ref_id": row.favorite_ref_id,
             **_describe(db, row)} for row in rows]


@router.post("")
def toggle_favorite(payload: FavoriteRequest, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    # Removing your own saved item always works, even once the listing is no longer shown;
    # only adding a new favorite needs the listing to be visible.
    already_saved = db.query(Favorite.id).filter(
        Favorite.user_id == user.id, Favorite.favorite_type == payload.favorite_type,
        Favorite.favorite_ref_id == payload.favorite_ref_id).first() is not None
    if not already_saved:
        _check_visible(db, payload.favorite_type, payload.favorite_ref_id)
    return {"favorited": FavoriteService(db).toggle_favorite(
        user_id=user.id, favorite_type=payload.favorite_type, favorite_ref_id=payload.favorite_ref_id,
    )}
