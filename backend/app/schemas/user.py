import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
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
