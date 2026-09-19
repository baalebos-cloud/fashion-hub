"""Email sending via SMTP or a transactional email API, selected by
EMAIL_PROVIDER. Called only from background workers (email_tasks.py), never
synchronously from a request handler."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.core.exceptions import ExternalProviderError


def send_email(*, to_address: str, subject: str, html_body: str) -> None:
    if settings.EMAIL_PROVIDER == "smtp":
        _send_via_smtp(to_address, subject, html_body)
    else:
        raise ExternalProviderError(f"Unsupported EMAIL_PROVIDER '{settings.EMAIL_PROVIDER}'")


def _send_via_smtp(to_address: str, subject: str, html_body: str) -> None:
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.EMAIL_FROM_ADDRESS
    message["To"] = to_address
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            if settings.EMAIL_USE_TLS:
                server.starttls()
            if settings.EMAIL_USERNAME and settings.EMAIL_PASSWORD:
                server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            server.send_message(message)
    except Exception as exc:  # noqa: BLE001
        raise ExternalProviderError(f"SMTP send failed: {exc}") from exc
