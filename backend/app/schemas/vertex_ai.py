"""AI drafts are advisory, not objective measurements derived from a photograph."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CustomerMeasurementSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bust: float | None = Field(default=None, gt=0, le=300)
    waist: float | None = Field(default=None, gt=0, le=300)
    hips: float | None = Field(default=None, gt=0, le=300)
    unit: Literal["cm", "in"] = "cm"
    confidence: float = Field(ge=0, le=1)
    requires_manual_measurement: bool = True
    notes: str = Field(max_length=1000)

    @model_validator(mode="after")
    def disallow_unverified_photo_dimensions(self):
        if not self.requires_manual_measurement:
            raise ValueError("Photographs are not a reliable tape measurement; confirmation is required.")
        return self


class MaterialRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    quantity_yards: float = Field(gt=0, le=100)
    note: str | None = Field(default=None, max_length=400)


class TailoringSpecSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    garment_description: str = Field(min_length=1, max_length=2000)
    estimated_fabric_yards: float = Field(gt=0, le=100)
    recommended_materials: list[MaterialRecommendation] = Field(max_length=30)
    assumptions: list[str] = Field(max_length=10)
    requires_tailor_review: bool = True
