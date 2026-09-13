"""SMS-specific background tasks."""
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.sms_tasks.send_sms_task", bind=True, max_retries=3)
def send_sms_task(self, phone_number: str, message: str):
    from app.core.exceptions import ExternalProviderError
    from app.integrations.notifications.sms import send_sms

    try:
        send_sms(to_phone=phone_number, message=message)
    except ExternalProviderError as exc:
        raise self.retry(exc=exc, countdown=30)
