import uuid
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class MeasurementFieldRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    field_name: str = Field(min_length=1, max_length=64, pattern=r'^[a-z][a-z0-9_]*$')
    value: Decimal = Field(gt=0, le=Decimal('9999.99'), max_digits=6, decimal_places=2)
    unit: Literal['cm', 'in'] = 'cm'


class CreateMeasurementProfileRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    label: str = Field(min_length=1, max_length=128)
    garment_type: str | None = Field(default=None, max_length=64)
    fields: list[MeasurementFieldRequest] = Field(min_length=1, max_length=64)

    @model_validator(mode='after')
    def unique_fields(self):
        if len({f.field_name for f in self.fields}) != len(self.fields):
            raise ValueError('Measurement field names must be unique.')
        return self


class MeasurementFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    field_name: str
    value: float
    unit: str


class MeasurementProfileResponse(BaseModel):
    id: uuid.UUID
    label: str
    garment_type: str | None
    fields: list[MeasurementFieldResponse]
