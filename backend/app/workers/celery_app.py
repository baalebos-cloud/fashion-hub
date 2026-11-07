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
        "app.workers.payment_outbox_tasks",
        "app.workers.invoice_tasks",
        "app.workers.delivery_tasks",
        "app.workers.tracking_tasks",
        "app.workers.notification_tasks",
        "app.workers.email_tasks",
        "app.workers.sms_tasks",
        "app.workers.whatsapp_tasks",
        "app.workers.push_tasks",
        "app.workers.kyc_tasks",
        "app.workers.image_tasks",
        "app.workers.ai_tasks",
        "app.workers.order_tasks",
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
        "app.workers.order_tasks.*": {"queue": "delivery"},
        "app.workers.payment_outbox_tasks.*": {"queue": "payments"},
        "app.workers.delivery_tasks.*": {"queue": "delivery"},
        "app.workers.tracking_tasks.*": {"queue": "delivery"},
        "app.workers.notification_tasks.*": {"queue": "notifications"},
        "app.workers.email_tasks.*": {"queue": "notifications"},
        "app.workers.sms_tasks.*": {"queue": "notifications"},
        "app.workers.whatsapp_tasks.*": {"queue": "notifications"},
        "app.workers.push_tasks.*": {"queue": "notifications"},
        "app.workers.invoice_tasks.*": {"queue": "invoices"},
        "app.workers.kyc_tasks.*": {"queue": "verification"},
        "app.workers.image_tasks.*": {"queue": "media"},
        "app.workers.ai_tasks.*": {"queue": "ai"},
    },
    beat_schedule={
        "sweep-sandbox-saga-orders": {
            "task": "app.workers.order_tasks.sweep_stale_saga_orders",
            "schedule": 300.0,
        },
        "drain-authentication-email-outbox": {
            "task": "app.workers.email_tasks.drain_auth_email_outbox",
            "schedule": 60.0,
        },
        "expire-material-stock-reservations": {
            "task": "app.workers.payment_tasks.expire_stock_reservations_task",
            "schedule": 30.0,
        },
        "drain-payment-outbox": {
            "task": "app.workers.payment_outbox_tasks.drain_payment_outbox",
            "schedule": 10.0,
        },
        "reconcile-pending-payments": {
            "task": "app.workers.payment_tasks.reconcile_pending_payments_task",
            "schedule": 300.0,  # every 5 minutes
        },
        "advance-expired-job-offers": {
            "task": "app.workers.delivery_tasks.advance_expired_job_offers_task",
            "schedule": 15.0,  # auto-dispatch exclusive windows (no-op while disabled)
        },
        "reconcile-courier-deliveries": {
            "task": "app.workers.delivery_tasks.reconcile_courier_deliveries_task",
            "schedule": 600.0,  # every 10 minutes; nothing to do until a courier is enabled
        },
        "check-stale-delivery-tracking": {
            "task": "app.workers.tracking_tasks.check_stale_tracking_task",
            "schedule": 120.0,  # every 2 minutes -- catches "GPS stopped updating"
        },
        "sync-shopping-history": {
            "task": "app.workers.notification_tasks.sync_interaction_history_task",
            "schedule": 86400.0,  # daily; copies cart adds, favourites and purchases for recommendations
        },
        "rebuild-related-items": {
            "task": "app.workers.notification_tasks.rebuild_item_similarities_task",
            "schedule": 86400.0,  # daily; learned "you might also like" / "often bought together"
        },
        "purge-old-shopping-activity": {
            "task": "app.workers.notification_tasks.purge_interactions_task",
            "schedule": 86400.0,  # daily; keeps INTERACTION_RETENTION_DAYS of history
        },
        "purge-old-activity-logs": {
            "task": "app.workers.notification_tasks.purge_activity_logs_task",
            "schedule": 86400.0,  # daily; keeps ACTIVITY_LOG_RETENTION_DAYS of history
        },
        "send-scheduled-reminders": {
            "task": "app.workers.notification_tasks.send_scheduled_reminders_task",
            "schedule": 3600.0,  # hourly
        },
    },
)
