import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserUpdateRequest(BaseModel):
    # Send the three parts (middle_name "" removes it). full_name alone is still accepted from
    # older app versions and is split into parts.
    first_name: Optional[str] = Field(None, max_length=200)
    middle_name: Optional[str] = Field(None, max_length=200)
    last_name: Optional[str] = Field(None, max_length=200)
    full_name: Optional[str] = Field(None, max_length=255)
    timezone: Optional[str] = None
    profile_photo_url: Optional[str] = None
    # Private -- never returned in UserPublicResponse or any schema another
    # user can see. Used only for platform notifications (see
    # notification_service.py's WhatsApp fan-out).
    whatsapp_number: Optional[str] = None


class CurrentUserResponse(BaseModel):
    """The full shape of 'who am I' -- GET/PATCH /users/me only. Includes
    whatsapp_number because a person can see and edit their OWN number;
    it's simply never included in any OTHER user's public profile (see
    UserPublicResponse below, which omits it)."""
    id: uuid.UUID
    email: EmailStr
    full_name: str
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    is_email_verified: bool
    is_phone_verified: bool
    profile_photo_url: Optional[str] = None
    timezone: str
    whatsapp_number: Optional[str] = None

    model_config = {"from_attributes": True}


class UserPublicResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    role: str
    profile_photo_url: Optional[str] = None

    model_config = {"from_attributes": True}
