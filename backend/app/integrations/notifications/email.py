"""Transactional email transports. Never expose a provider key or provider response to callers."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError


def provider_status() -> dict:
    """Whether outgoing email can work with the current settings, without sending anything."""
    if settings.EMAIL_PROVIDER == "resend":
        if not settings.EMAIL_API_KEY:
            return {"ready": False, "provider": "resend", "problem": "EMAIL_API_KEY is not set."}
        if not settings.EMAIL_FROM_ADDRESS or settings.EMAIL_FROM_ADDRESS.endswith(".example"):
            return {"ready": False, "provider": "resend",
                    "problem": "EMAIL_FROM_ADDRESS must be an address on a domain verified in Resend."}
        return {"ready": True, "provider": "resend", "problem": None, "from": settings.EMAIL_FROM_ADDRESS}
    if settings.EMAIL_PROVIDER == "smtp":
        if settings.EMAIL_HOST in {"", "localhost", "127.0.0.1"} and settings.APP_ENV in {"staging", "production"}:
            return {"ready": False, "provider": "smtp", "problem": "EMAIL_HOST points at localhost; set a real SMTP relay."}
        if settings.EMAIL_FROM_ADDRESS.endswith(".example"):
            return {"ready": False, "provider": "smtp", "problem": "EMAIL_FROM_ADDRESS is still the placeholder."}
        return {"ready": True, "provider": "smtp", "problem": None, "from": settings.EMAIL_FROM_ADDRESS}
    return {"ready": False, "provider": settings.EMAIL_PROVIDER, "problem": "EMAIL_PROVIDER must be resend or smtp."}


def send_email(*, to_address: str, subject: str, html_body: str,
               idempotency_key: str | None = None) -> None:
    """Deliver transactional email. A stable key prevents duplicate Resend sends on retries."""
    if settings.EMAIL_PROVIDER == "resend":
        _send_via_resend(to_address, subject, html_body, idempotency_key)
    elif settings.EMAIL_PROVIDER == "smtp":
        _send_via_smtp(to_address, subject, html_body)
    else:
        raise ExternalProviderError("Email provider is not configured.")


def _send_via_resend(to_address: str, subject: str, html_body: str,
                     idempotency_key: str | None) -> None:
    if not settings.EMAIL_API_KEY or not settings.EMAIL_FROM_ADDRESS or settings.EMAIL_FROM_ADDRESS.endswith(".example"):
        raise ExternalProviderError("Resend requires an API key and a verified sender domain.")
    headers = {
        "Authorization": f"Bearer {settings.EMAIL_API_KEY}",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers=headers,
            json={"from": settings.EMAIL_FROM_ADDRESS, "to": [to_address],
                  "subject": subject, "html": html_body},
            timeout=12.0,
        )
    except httpx.RequestError:
        raise ExternalProviderError("Resend delivery endpoint is unreachable.") from None
    if response.status_code not in {200, 201, 202}:
        # In particular, do not log the response body. It can contain provider PII.
        raise ExternalProviderError(f"Resend rejected the email (HTTP {response.status_code}).")


def _send_via_smtp(to_address: str, subject: str, html_body: str) -> None:
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.EMAIL_FROM_ADDRESS
    message["To"] = to_address
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=12) as server:
            if settings.EMAIL_USE_TLS:
                server.starttls()
            if settings.EMAIL_USERNAME and settings.EMAIL_PASSWORD:
                server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            server.send_message(message)
    except (OSError, smtplib.SMTPException):
        raise ExternalProviderError("SMTP delivery failed.") from None
