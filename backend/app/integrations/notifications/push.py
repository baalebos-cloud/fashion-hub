"""Push notification abstraction (e.g. Firebase Cloud Messaging), selected
by PUSH_PROVIDER."""
from app.core.config import settings
from app.core.exceptions import ExternalProviderError


def send_push(*, device_token: str, title: str, body: str, data: dict | None = None) -> None:
    if not settings.PUSH_PROVIDER:
        raise ExternalProviderError("No PUSH_PROVIDER configured.")
    raise NotImplementedError(f"Push provider '{settings.PUSH_PROVIDER}' integration not yet implemented.")
