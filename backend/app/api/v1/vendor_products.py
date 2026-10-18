"""Public verified catalog and vendor-owned publishing."""
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_current_user
from app.core.permissions import Role, require_roles
from app.models.user import User
from app.schemas.vendor_product import VendorProductCreateRequest, VendorProductUpdateRequest, VendorProductResponse, VendorProductsResponse
from app.services.vendor_catalog_service import VendorCatalogService

router = APIRouter(prefix='/vendor-products', tags=['Vendor Products'])


@router.get('', response_model=VendorProductsResponse)
def list_products(pagination: PaginationParams = Depends(), vendor_id: uuid.UUID | None = None,
                  category_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    return VendorCatalogService(db).list(pagination, vendor_id=vendor_id, category_id=category_id)


@router.get('/mine', response_model=VendorProductsResponse)
def my_products(pagination: PaginationParams = Depends(), user: User = Depends(require_roles(Role.VENDOR)), db: Session = Depends(get_db)):
    return VendorCatalogService(db).list(pagination, owner_user_id=user.id)


@router.get('/{product_id}', response_model=VendorProductResponse)
def product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    return VendorCatalogService(db).get(product_id)


@router.post('', response_model=VendorProductResponse, status_code=201)
def create(payload: VendorProductCreateRequest, user: User = Depends(require_roles(Role.VENDOR)), db: Session = Depends(get_db)):
    return VendorCatalogService(db).create(user.id, payload)


@router.patch('/{product_id}', response_model=VendorProductResponse)
def update(product_id: uuid.UUID, payload: VendorProductUpdateRequest, user: User = Depends(require_roles(Role.VENDOR)), db: Session = Depends(get_db)):
    return VendorCatalogService(db).update(user.id, product_id, payload)
