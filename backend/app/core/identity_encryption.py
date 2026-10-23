"""Encryption for identity values. Use a dedicated key, never the JWT secret."""
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
