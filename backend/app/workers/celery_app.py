"""
Celery app configuration. Broker/backend point at Redis (separate logical
DBs from the app cache -- see CELERY_BROKER_URL / CELERY_RESULT_BACKEND in
config.py) so a flushed cache never wipes in-flight job state.

Run a worker with: celery -A app.workers.celery_app worker --loglevel=info
Run beat (scheduled jobs) with: celery -A app.workers.celery_app beat --loglevel=info
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "fashion_hub",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.payment_tasks",
        "app.workers.invoice_tasks",
        "app.workers.delivery_tasks",
        "app.workers.tracking_tasks",
        "app.workers.notification_tasks",
        "app.workers.email_tasks",
        "app.workers.sms_tasks",
        "app.workers.push_tasks",
        "app.workers.kyc_tasks",
        "app.workers.image_tasks",
        "app.workers.ai_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,  # redeliver a task if the worker crashes mid-execution
    worker_prefetch_multiplier=1,
    task_default_retry_delay=30,
    task_routes={
        "app.workers.payment_tasks.*": {"queue": "payments"},
        "app.workers.delivery_tasks.*": {"queue": "delivery"},
        "app.workers.tracking_tasks.*": {"queue": "delivery"},
        "app.workers.notification_tasks.*": {"queue": "notifications"},
        "app.workers.email_tasks.*": {"queue": "notifications"},
        "app.workers.sms_tasks.*": {"queue": "notifications"},
        "app.workers.push_tasks.*": {"queue": "notifications"},
        "app.workers.invoice_tasks.*": {"queue": "invoices"},
        "app.workers.kyc_tasks.*": {"queue": "verification"},
        "app.workers.image_tasks.*": {"queue": "media"},
        "app.workers.ai_tasks.*": {"queue": "ai"},
    },
    beat_schedule={
        "reconcile-pending-payments": {
            "task": "app.workers.payment_tasks.reconcile_pending_payments_task",
            "schedule": 300.0,  # every 5 minutes
        },
        "check-stale-delivery-tracking": {
            "task": "app.workers.tracking_tasks.check_stale_tracking_task",
            "schedule": 120.0,  # every 2 minutes -- catches "GPS stopped updating"
        },
        "send-scheduled-reminders": {
            "task": "app.workers.notification_tasks.send_scheduled_reminders_task",
            "schedule": 3600.0,  # hourly
        },
    },
)
