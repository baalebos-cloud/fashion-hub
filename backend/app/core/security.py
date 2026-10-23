"""
Security primitives: password hashing, JWT issuing/verification.

Kept deliberately provider-agnostic and side-effect-free so it can be unit
tested without a database or network. Business rules (e.g. "is this user
allowed to reset their password") belong in services, not here.
"""
import uuid
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from jwt import InvalidTokenError as JWTError
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError
from passlib.context import CryptContext

from app.core.config import settings

# New credentials use Argon2id; the older schemes remain verification-only
# so existing customers can sign in and upgrade without a password reset.
password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4,
                                 hash_len=32, salt_len=16, type=Type.ID)
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if hashed_password.startswith("$argon2"):
            return password_hasher.verify(hashed_password, plain_password)
        return pwd_context.verify(plain_password, hashed_password)
    except (InvalidHashError, VerificationError, ValueError, TypeError):
        return False


def verify_and_update_password(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    if not verify_password(plain_password, hashed_password):
        return False, None
    if not hashed_password.startswith("$argon2id$") or password_hasher.check_needs_rehash(hashed_password):
        return True, hash_password(plain_password)
    return True, None


def _create_token(subject: str, expires_delta: timedelta, token_type: str, extra_claims: Optional[dict] = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        **(extra_claims or {}),
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, role: str, extra_claims: Optional[dict] = None) -> str:
    claims = {**(extra_claims or {}), "role": role}
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


def password_version(password_hash: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), password_hash.encode(), hashlib.sha256).hexdigest()


def create_password_reset_token(user_id: str, password_hash: str) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
        token_type="password_reset",
        extra_claims={"password_version": password_version(password_hash)},
    )


def decode_token(token: str, expected_type: Optional[str] = None) -> dict:
    """
    Raises JWTError (or ValueError for wrong type) on any problem.
    Callers should catch and translate into an HTTP 401.
    """
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "iat", "exp", "jti", "type"]},
    )
    if not payload["sub"] or not isinstance(payload["jti"], str) or not payload["jti"]:
        raise JWTError("Invalid token identity.")
    if expected_type and payload.get("type") != expected_type:
        raise ValueError(f"Expected token type '{expected_type}', got '{payload.get('type')}'")
    return payload


__all__ = [
    "hash_password",
    "verify_password",
    "verify_and_update_password",
    "create_access_token",
    "create_refresh_token",
    "create_email_verification_token",
    "create_password_reset_token",
    "decode_token",
    "JWTError",
]
