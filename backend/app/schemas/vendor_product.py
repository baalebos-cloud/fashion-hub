import uuid
from typing import Literal
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator


class ColourOption(BaseModel):
    model_config = {'extra': 'forbid', 'str_strip_whitespace': True}
    name: str = Field(min_length=1, max_length=40)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    stock: int = Field(0, ge=0, le=1000000000, strict=True)


class VendorProductCreateRequest(BaseModel):
    model_config = {'extra': 'forbid', 'str_strip_whitespace': True}
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    base_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    image_urls: list[str] = Field(default_factory=list, max_length=5)
    unit_of_measure: Literal['yard', 'meter', 'roll', 'piece'] = 'yard'
    initial_stock: int = Field(0, ge=0, le=1000000000, strict=True)
    category_id: uuid.UUID | None = None
    # Optional: one version per colour, each with its own price and stock. When given, the
    # product's base price is the lowest colour price and initial_stock must be left at 0.
    colours: list[ColourOption] | None = Field(None, min_length=1, max_length=20)

    @model_validator(mode='after')
    def _colours_are_distinct(self):
        if self.colours:
            names = [c.name.casefold() for c in self.colours]
            if len(set(names)) != len(names):
                raise ValueError('Each colour needs a different name.')
            if self.initial_stock:
                raise ValueError('Set stock per colour, not initial_stock, when listing colours.')
        return self


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
    unit_of_measure: str
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
