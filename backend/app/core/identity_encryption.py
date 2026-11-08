"""Encryption for identity values. Use a dedicated key, never the JWT secret."""
import hashlib
import hmac

from cryptography.fernet import Fernet
from app.core.config import settings
from app.core.exceptions import ExternalProviderError


def encrypt_identity(value: str) -> str:
    if not settings.IDENTITY_ENCRYPTION_KEY:
        raise ExternalProviderError("Identity storage is not configured.")
    try:
        cipher = Fernet(settings.IDENTITY_ENCRYPTION_KEY.encode())
    except (ValueError, TypeError) as exc:
        raise ExternalProviderError("Identity storage is not configured.") from exc
    return "fernet:v1:" + cipher.encrypt(value.encode()).decode()


def identity_fingerprint(value: str) -> str:
    """Keyed one-way fingerprint, so the same NIN can be spotted on two accounts without
    storing it readably. Keyed from the identity key, so it can't be brute-forced without it."""
    if not settings.IDENTITY_ENCRYPTION_KEY:
        raise ExternalProviderError("Identity storage is not configured.")
    key = hmac.new(settings.IDENTITY_ENCRYPTION_KEY.encode(), b"tailora:nin-fingerprint:v1", hashlib.sha256).digest()
    return hmac.new(key, value.strip().encode(), hashlib.sha256).hexdigest()
