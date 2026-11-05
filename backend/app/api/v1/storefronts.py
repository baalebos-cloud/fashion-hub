"""
/storefronts

Shareable shop links (tailora.app/s/<handle>) for tailors, designers and
vendors, e.g. for a WhatsApp status. The public page shows only verified,
active shops and only public business data: no owner email, phone, exact
address, ID details or customer names beyond a reviewer's first name.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.permissions import Role, require_roles
from app.models.design import Design
from app.models.location import Location
from app.models.professional import Professional
from app.models.rating import Rating
from app.models.review import Review
from app.models.storefront_handle import StorefrontHandle
from app.models.user import User
from app.models.vendor import Vendor
from app.models.vendor_product import VendorProduct
from app.services.storefront_handles import candidate_handles, is_valid_handle

router = APIRouter(prefix="/storefronts", tags=["Storefronts"])

MAX_CATALOGUE_ITEMS = 24
MAX_REVIEWS = 6


class StorefrontLink(BaseModel):
    handle: str
    share_url: str
    is_public: bool
    status_message: str


class UpdateHandleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    handle: str = Field(min_length=3, max_length=30)


def share_url(handle: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/s/{handle}"


def _owner_profile(db: Session, user: User):
    if user.role == "vendor":
        return "vendor", db.query(Vendor).filter(Vendor.user_id == user.id).first()
    return "professional", db.query(Professional).filter(Professional.user_id == user.id).first()


def _ensure_handle(db: Session, user: User) -> tuple[StorefrontHandle, object]:
    owner_type, profile = _owner_profile(db, user)
    if profile is None:
        raise NotFoundError("Create your shop profile first, then your link is generated automatically.")
    existing = db.query(StorefrontHandle).filter(StorefrontHandle.owner_user_id == user.id).first()
    if existing:
        return existing, profile
    for candidate in candidate_handles(getattr(profile, "business_name", None), str(user.id)):
        if db.query(StorefrontHandle.id).filter(StorefrontHandle.handle == candidate).first():
            continue
        record = StorefrontHandle(handle=candidate, owner_user_id=user.id, owner_type=owner_type)
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # Lost a race for this handle; try the next one.
            continue
        db.refresh(record)
        return record, profile
    raise ConflictError("Could not generate a shop link. Choose one yourself.")


def _link(record: StorefrontHandle, profile) -> StorefrontLink:
    public = bool(getattr(profile, "is_verified", False))
    return StorefrontLink(
        handle=record.handle, share_url=share_url(record.handle), is_public=public,
        status_message=("Your link is live. Share it on your WhatsApp status or social pages."
                        if public else
                        "Your link is reserved. It goes live once Tailora verifies your shop."),
    )


@router.get("/me", response_model=StorefrontLink)
def my_storefront_link(user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER, Role.VENDOR)),
                       db: Session = Depends(get_db)):
    record, profile = _ensure_handle(db, user)
    return _link(record, profile)


@router.put("/me", response_model=StorefrontLink)
def change_storefront_handle(payload: UpdateHandleRequest,
                             user: User = Depends(require_roles(Role.TAILOR, Role.DESIGNER, Role.VENDOR)),
                             db: Session = Depends(get_db)):
    handle = payload.handle.lower()
    if not is_valid_handle(handle):
        raise ValidationAppError(
            "Use 3–30 lowercase letters, numbers and single hyphens, starting and ending with a "
            "letter or number. Some words, like 'tailora' or 'support', are reserved.")
    record, profile = _ensure_handle(db, user)
    if record.handle == handle:
        return _link(record, profile)
    if db.query(StorefrontHandle.id).filter(StorefrontHandle.handle == handle).first():
        raise ConflictError("That link is already taken. Try another.")
    record.handle = handle
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("That link is already taken. Try another.") from None
    db.refresh(record)
    return _link(record, profile)


def _area(db: Session, location_id) -> str | None:
    """City and state only; never the street address or coordinates."""
    if not location_id:
        return None
    location = db.get(Location, location_id)
    if location is None:
        return None
    parts = [p for p in (location.city, location.state_region) if p]
    return ", ".join(dict.fromkeys(parts)) or None


def _reviews(db: Session, owner_user_id) -> list[dict]:
    rows = (db.query(Review, User.full_name, Rating.score)
            .join(User, User.id == Review.reviewer_user_id)
            .outerjoin(Rating, (Rating.review_id == Review.id) & (Rating.axis == "overall"))
            .filter(Review.reviewee_user_id == owner_user_id)
            .order_by(desc(Review.created_at)).limit(MAX_REVIEWS).all())
    reviews = []
    for review, reviewer_name, score in rows:
        first = (reviewer_name or "").strip().split(" ")[0] if reviewer_name else ""
        reviews.append({"id": str(review.id), "reviewer_first_name": first or "Customer",
                        "score": score, "comment": review.comment, "created_at": review.created_at})
    return reviews


@router.get("/{handle}")
def public_storefront(handle: str, db: Session = Depends(get_db)):
    handle = handle.lower()
    if not is_valid_handle(handle) and not handle.startswith("shop-"):
        raise NotFoundError("Shop not found.")
    record = db.query(StorefrontHandle).filter(StorefrontHandle.handle == handle).first()
    owner = db.get(User, record.owner_user_id) if record else None
    if record is None or owner is None or not owner.is_active:
        raise NotFoundError("Shop not found.")

    base = {"handle": record.handle, "share_url": share_url(record.handle),
            "member_since": owner.created_at.year if owner.created_at else None,
            "profile_photo_url": owner.profile_photo_url,
            "reviews": _reviews(db, owner.id)}

    if record.owner_type == "vendor":
        vendor = db.query(Vendor).filter(Vendor.user_id == owner.id).first()
        if vendor is None or not vendor.is_verified:
            raise NotFoundError("Shop not found.")
        products = (db.query(VendorProduct)
                    .filter(VendorProduct.vendor_id == vendor.id, VendorProduct.is_active.is_(True))
                    .order_by(desc(VendorProduct.created_at)).limit(MAX_CATALOGUE_ITEMS).all())
        return {**base, "kind": "vendor", "vendor_id": str(vendor.id),
                "display_name": vendor.business_name, "bio": vendor.business_description,
                "is_verified": True, "average_rating": float(vendor.average_rating or 0),
                "review_count": int(db.query(func.count(Review.id))
                                    .filter(Review.reviewee_user_id == owner.id).scalar() or 0),
                "area": _area(db, vendor.warehouse_location_id), "accepts_new_orders": True,
                "years_experience": None,
                "products": [{"id": str(p.id), "name": p.name, "base_price": float(p.base_price),
                              "currency": p.currency, "unit_of_measure": p.unit_of_measure,
                              "image_url": p.primary_image_url} for p in products],
                "designs": [], "portfolio": []}

    professional = db.query(Professional).filter(Professional.user_id == owner.id).first()
    if professional is None or (not professional.is_verified
                                and not settings.HACKATHON_SHOW_PENDING_PROFESSIONALS):
        raise NotFoundError("Shop not found.")
    designs = (db.query(Design)
               .filter(Design.professional_id == professional.id, Design.is_published.is_(True))
               .order_by(desc(Design.created_at)).limit(MAX_CATALOGUE_ITEMS).all())
    from app.api.v1.professionals import public_portfolio
    try:
        portfolio = public_portfolio(professional.id, db)[:MAX_CATALOGUE_ITEMS]
    except NotFoundError:
        portfolio = []
    return {**base, "kind": professional.professional_type, "professional_id": str(professional.id),
            "display_name": professional.business_name or "Tailora professional",
            "bio": professional.bio, "is_verified": bool(professional.is_verified),
            "average_rating": float(professional.average_rating or 0),
            "review_count": professional.review_count,
            "years_experience": professional.years_experience,
            "accepts_new_orders": professional.accepts_new_orders,
            "area": _area(db, professional.location_id),
            "designs": [{"id": str(d.id), "title": d.title, "base_price": float(d.base_price),
                         "currency": d.currency, "estimated_turnaround_days": d.estimated_turnaround_days}
                        for d in designs],
            "portfolio": portfolio, "products": []}
