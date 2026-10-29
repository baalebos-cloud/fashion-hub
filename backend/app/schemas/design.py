import uuid
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class CreateDesignRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    image_url: str | None = Field(None, max_length=1024)
    description: Optional[str] = None
    base_price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    category_id: Optional[uuid.UUID] = None
    # e.g. ["chest", "waist", "sleeve_length"] -- the tailor/designer's own
    # required fields for this specific design. Left null/empty, the
    # customer's full default measurement profile applies as-is (see
    # docs/measurement-requirements.md -- "or client filled it themselves").
    required_measurement_fields: Optional[list[str]] = None


class DesignResponse(BaseModel):
    image_url: str | None = None
    id: uuid.UUID
    professional_id: uuid.UUID
    title: str
    description: Optional[str] = None
    currency: str
    base_price: float
    is_published: bool
    required_measurement_fields: Optional[list[str]] = None

    model_config = {"from_attributes": True}
