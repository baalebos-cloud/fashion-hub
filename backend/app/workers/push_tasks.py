"""Push-notification-specific background tasks."""
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.push_tasks.send_push_task", bind=True, max_retries=3)
def send_push_task(self, device_token: str, title: str, body: str):
    from app.core.exceptions import ExternalProviderError
    from app.integrations.notifications.push import send_push

    try:
        send_push(device_token=device_token, title=title, body=body)
    except ExternalProviderError as exc:
        raise self.retry(exc=exc, countdown=30)
