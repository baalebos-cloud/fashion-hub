import uuid
from typing import Optional
from pydantic import BaseModel


class MeasurementFieldInput(BaseModel):
    field_name: str
    value: float
    unit: str = "cm"


class CreateMeasurementProfileRequest(BaseModel):
    label: str
    garment_type: Optional[str] = None
    fields: list[MeasurementFieldInput]


class MeasurementProfileResponse(BaseModel):
    id: uuid.UUID
    label: str
    garment_type: Optional[str] = None

    model_config = {"from_attributes": True}
