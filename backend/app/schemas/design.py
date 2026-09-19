import uuid
from typing import Optional
from pydantic import BaseModel, Field


class CreateDesignRequest(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    base_price: float = Field(..., gt=0)
    category_id: Optional[uuid.UUID] = None
    # e.g. ["chest", "waist", "sleeve_length"] -- the tailor/designer's own
    # required fields for this specific design. Left null/empty, the
    # customer's full default measurement profile applies as-is (see
    # docs/measurement-requirements.md -- "or client filled it themselves").
    required_measurement_fields: Optional[list[str]] = None


class DesignResponse(BaseModel):
    id: uuid.UUID
    title: str
    base_price: float
    is_published: bool
    required_measurement_fields: Optional[list[str]] = None

    model_config = {"from_attributes": True}
