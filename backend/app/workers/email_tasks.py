"""Email-specific background tasks. Retries with backoff on transient
provider failures rather than dropping the email silently."""
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.email_tasks.send_verification_email_task", bind=True, max_retries=3)
def send_verification_email_task(self, user_email: str, token: str):
    from app.core.config import settings
    from app.core.exceptions import ExternalProviderError
    from app.integrations.notifications.email import send_email

    verify_url = f"{settings.APP_URL}/verify-email?token={token}"
    try:
        send_email(
            to_address=user_email,
            subject="Verify your Fashion Hub account",
            html_body=f"<p>Welcome! Please verify your email: <a href='{verify_url}'>{verify_url}</a></p>",
        )
    except ExternalProviderError as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="app.workers.email_tasks.send_password_reset_email_task", bind=True, max_retries=3)
def send_password_reset_email_task(self, user_email: str, token: str):
    from app.core.config import settings
    from app.core.exceptions import ExternalProviderError
    from app.integrations.notifications.email import send_email

    reset_url = f"{settings.APP_URL}/reset-password?token={token}"
    try:
        send_email(
            to_address=user_email,
            subject="Reset your Fashion Hub password",
            html_body=f"<p>Reset your password: <a href='{reset_url}'>{reset_url}</a></p>",
        )
    except ExternalProviderError as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="app.workers.email_tasks.send_invoice_email_task", bind=True, max_retries=3)
def send_invoice_email_task(self, user_email: str, invoice_pdf_url: str):
    from app.core.exceptions import ExternalProviderError
    from app.integrations.notifications.email import send_email

    try:
        send_email(
            to_address=user_email,
            subject="Your Fashion Hub invoice",
            html_body=f"<p>Your invoice is ready: <a href='{invoice_pdf_url}'>{invoice_pdf_url}</a></p>",
        )
    except ExternalProviderError as exc:
        raise self.retry(exc=exc, countdown=30)
