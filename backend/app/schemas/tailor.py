import uuid
from typing import Optional
from pydantic import BaseModel


class TailorResponse(BaseModel):
    id: uuid.UUID
    garment_specialties: Optional[list[str]] = None
    turnaround_time_days: Optional[int] = None

    model_config = {"from_attributes": True}
