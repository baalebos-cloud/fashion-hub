"""Related products: 'You might also like' on product pages and 'Often bought together' in the
cart, and "Picked for you" on the materials marketplace. Public; no personal data comes out."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_optional_current_user
from app.models.user import User
from app.services import personal_ranking_service, related_items_service

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


class RelatedProduct(BaseModel):
    product_id: UUID
    name: str
    vendor_name: str
    primary_image_url: str | None
    price_ngn: float
    currency: str
    unit_of_measure: str
    # bought_together / viewed_together / for_you / trending are learned;
    # similar / same_vendor / new_in are fixed rules.
    reason: Literal["bought_together", "viewed_together", "similar", "same_vendor", "for_you", "trending", "new_in"]
    learned: bool


class RelatedProducts(BaseModel):
    items: list[RelatedProduct]


class RankedProducts(RelatedProducts):
    ranking: Literal["rules", "learned"]


@router.get("/products/{product_id}/similar", response_model=RelatedProducts)
def similar_products(product_id: UUID, limit: int = Query(8, ge=1, le=20), db: Session = Depends(get_db)):
    return {"items": related_items_service.similar_products(db, product_id, limit)}


@router.get("/products/bought-together", response_model=RelatedProducts)
def bought_together(product_id: list[UUID] = Query(..., min_length=1, max_length=50),
                    limit: int = Query(6, ge=1, le=20), db: Session = Depends(get_db)):
    return {"items": related_items_service.bought_together(db, list(dict.fromkeys(product_id)), limit)}


@router.get("/products/picked-for-you", response_model=RankedProducts)
def picked_for_you(browser_id: UUID | None = None, limit: int = Query(8, ge=1, le=20),
                   user: User | None = Depends(get_optional_current_user), db: Session = Depends(get_db)):
    """Signed-out visitors pass their random browser ID (the same one used for shopping
    activity); without it, or with personalisation off, the fixed ordering is used."""
    assignment = personal_ranking_service.assign(user, str(browser_id) if browser_id else None)
    items = related_items_service.picked_for_you(db, assignment, limit)
    return {"items": items, "ranking": assignment.variant}
