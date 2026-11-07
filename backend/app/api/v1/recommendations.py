"""Related products: 'You might also like' on product pages and 'Often bought together' in the
cart. Public and read-only; no personal data goes in or comes out."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import related_items_service

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


class RelatedProduct(BaseModel):
    product_id: UUID
    name: str
    vendor_name: str
    primary_image_url: str | None
    price_ngn: float
    currency: str
    unit_of_measure: str
    # bought_together / viewed_together are learned; similar / same_vendor are fallbacks.
    reason: Literal["bought_together", "viewed_together", "similar", "same_vendor"]
    learned: bool


class RelatedProducts(BaseModel):
    items: list[RelatedProduct]


@router.get("/products/{product_id}/similar", response_model=RelatedProducts)
def similar_products(product_id: UUID, limit: int = Query(8, ge=1, le=20), db: Session = Depends(get_db)):
    return {"items": related_items_service.similar_products(db, product_id, limit)}


@router.get("/products/bought-together", response_model=RelatedProducts)
def bought_together(product_id: list[UUID] = Query(..., min_length=1, max_length=50),
                    limit: int = Query(6, ge=1, le=20), db: Session = Depends(get_db)):
    return {"items": related_items_service.bought_together(db, list(dict.fromkeys(product_id)), limit)}
