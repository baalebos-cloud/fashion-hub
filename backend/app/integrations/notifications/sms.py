"""SMS sending abstraction, selected by SMS_PROVIDER (e.g. Termii, Twilio)."""
from app.core.config import settings
from app.core.exceptions import ExternalProviderError


def send_sms(*, to_phone: str, message: str) -> None:
    if not settings.SMS_PROVIDER:
        raise ExternalProviderError("No SMS_PROVIDER configured.")
    # Concrete provider call goes here, e.g.:
    # httpx.post(f"https://api.{settings.SMS_PROVIDER}.com/sms/send", json={...})
    raise NotImplementedError(f"SMS provider '{settings.SMS_PROVIDER}' integration not yet implemented.")
