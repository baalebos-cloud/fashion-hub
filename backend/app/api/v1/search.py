"""Search verified professionals, published designs and active vendor materials."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ValidationAppError
from app.schemas.professional import ProfessionalResponse
from app.schemas.design import DesignResponse
from app.schemas.vendor_product import VendorProductResponse
from app.core.rate_limit import limiter
from app.services import smart_search_service
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/professionals", response_model=list[ProfessionalResponse])
def professionals(q: str = Query(min_length=1, max_length=200),
                  lat: float | None = Query(None, ge=-90, le=90),
                  lng: float | None = Query(None, ge=-180, le=180),
                  radius_km: float = Query(20, gt=0, le=200),
                  db: Session = Depends(get_db)):
    if (lat is None) != (lng is None):
        raise ValidationAppError("Provide both latitude and longitude.")
    return SearchService(db).search_professionals(
        query=q, latitude=lat, longitude=lng, radius_km=radius_km,
    )


@router.get("/designs", response_model=list[DesignResponse])
def designs(q: str = Query(min_length=1, max_length=200),
            min_price: float | None = Query(None, ge=0),
            max_price: float | None = Query(None, ge=0),
            db: Session = Depends(get_db)):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValidationAppError("Minimum price must not exceed maximum price.")
    return SearchService(db).search_designs(query=q, min_price=min_price, max_price=max_price)


@router.get("/vendor-products", response_model=list[VendorProductResponse])
def products(q: str = Query(min_length=1, max_length=200),
             category_id: UUID | None = Query(None), db: Session = Depends(get_db)):
    return SearchService(db).search_vendor_products(query=q, category_id=category_id)


class SmartFilters(BaseModel):
    keywords: list[str]
    min_price: float | None
    max_price: float | None


class SmartDesign(DesignResponse):
    professional_name: str | None = None


class SmartSearchResult(BaseModel):
    understood_by: str  # "ai" or "keywords"
    filters: SmartFilters
    designs: list[SmartDesign]


@router.get("/smart", response_model=SmartSearchResult)
@limiter.limit("30/minute")
def smart(request: Request, q: str = Query(min_length=2, max_length=200),
          limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db)):
    """Describe what you want in your own words. Returns the filters it understood (so the page
    can show them) and matching designs from verified tailors."""
    filters, understood_by = smart_search_service.understand(q)
    rows = smart_search_service.search_designs(db, filters, limit) if not filters.empty() else []
    designs = []
    for design, professional in rows:
        item = SmartDesign.model_validate(design)
        item.professional_name = professional.business_name
        designs.append(item)
    return {"understood_by": understood_by,
            "filters": {"keywords": filters.keywords, "min_price": filters.min_price, "max_price": filters.max_price},
            "designs": designs}
