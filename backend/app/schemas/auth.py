import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignUpRequest(BaseModel):
    email: EmailStr
    phone_number: Optional[str] = Field(None, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(..., description="customer | tailor | designer | vendor | delivery_partner")

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter.")
        return v


class LogInRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_email_verified: bool
    is_phone_verified: bool

    model_config = {"from_attributes": True}
