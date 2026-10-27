"""Search verified professionals, published designs and active vendor materials."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ValidationAppError
from app.schemas.professional import ProfessionalResponse
from app.schemas.design import DesignResponse
from app.schemas.vendor_product import VendorProductResponse
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
