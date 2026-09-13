"""
Security primitives: password hashing, JWT issuing/verification.

Kept deliberately provider-agnostic and side-effect-free so it can be unit
tested without a database or network. Business rules (e.g. "is this user
allowed to reset their password") belong in services, not here.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, expires_delta: timedelta, token_type: str, extra_claims: Optional[dict] = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, role: str, extra_claims: Optional[dict] = None) -> str:
    claims = {"role": role}
    if extra_claims:
        claims.update(extra_claims)
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
        extra_claims=claims,
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def create_email_verification_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES),
        token_type="email_verification",
    )


def create_password_reset_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
        token_type="password_reset",
    )


def decode_token(token: str, expected_type: Optional[str] = None) -> dict:
    """
    Raises jose.JWTError (or ValueError for wrong type) on any problem.
    Callers should catch and translate into an HTTP 401.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if expected_type and payload.get("type") != expected_type:
        raise ValueError(f"Expected token type '{expected_type}', got '{payload.get('type')}'")
    return payload


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "create_email_verification_token",
    "create_password_reset_token",
    "decode_token",
    "JWTError",
]
