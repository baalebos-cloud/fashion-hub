import uuid
from typing import Optional
from pydantic import BaseModel


class DesignerResponse(BaseModel):
    id: uuid.UUID
    style_tags: Optional[list[str]] = None
    signature_collection: Optional[str] = None

    model_config = {"from_attributes": True}
