import uuid
from decimal import Decimal
from pydantic import BaseModel, Field


class VendorProductCreateRequest(BaseModel):
    model_config = {'extra': 'forbid', 'str_strip_whitespace': True}
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    base_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    image_urls: list[str] = Field(default_factory=list, min_length=1, max_length=5)
    initial_stock: int = Field(0, ge=0, le=1000000000, strict=True)
    category_id: uuid.UUID | None = None


class VendorProductUpdateRequest(BaseModel):
    model_config = {'extra': 'forbid', 'str_strip_whitespace': True}
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    is_active: bool = True


class VariantResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    attributes: dict | None = None
    price: float
    quantity_available: int


class VendorProductResponse(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    vendor_name: str
    name: str
    description: str | None
    category_id: uuid.UUID | None
    image_urls: list[str]
    primary_image_url: str | None
    base_price: float
    currency: str
    is_active: bool
    variants: list[VariantResponse]


class VendorProductsResponse(BaseModel):
    items: list[VendorProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
