"""WhatsApp-specific background tasks."""
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.whatsapp_tasks.send_whatsapp_task", bind=True, max_retries=3)
def send_whatsapp_task(self, to_phone: str, template_name: str, template_params: list[str] | None = None):
    from app.core.exceptions import ExternalProviderError
    from app.integrations.notifications.whatsapp import send_whatsapp_message

    try:
        send_whatsapp_message(to_phone=to_phone, template_name=template_name, template_params=template_params)
    except ExternalProviderError as exc:
        raise self.retry(exc=exc, countdown=30)
