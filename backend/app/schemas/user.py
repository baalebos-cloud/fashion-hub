import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    timezone: Optional[str] = None


class UserPublicResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    role: str
    profile_photo_url: Optional[str] = None

    model_config = {"from_attributes": True}
