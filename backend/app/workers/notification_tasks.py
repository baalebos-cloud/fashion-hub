"""
Dispatches notifications across channels (in-app always; email/SMS/push
where configured) for domain events. All notification sending is
background-only so a slow email/SMS provider never blocks an API request.
"""
from app.core.database import session_scope
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.notification_tasks.notify_order_status_changed_task")
def notify_order_status_changed_task(order_id: str, new_status: str):
    with session_scope() as db:
        from app.services.notification_service import NotificationService
        NotificationService(db).notify_order_status_changed(order_id=order_id, new_status=new_status)


@celery_app.task(name="app.workers.notification_tasks.notify_delivery_tracking_stale_task")
def notify_delivery_tracking_stale_task(delivery_id: str):
    with session_scope() as db:
        from app.services.notification_service import NotificationService
        NotificationService(db).notify_delivery_tracking_stale(delivery_id=delivery_id)


@celery_app.task(name="app.workers.notification_tasks.send_scheduled_reminders_task")
def send_scheduled_reminders_task():
    with session_scope() as db:
        from app.services.notification_service import NotificationService
        NotificationService(db).send_scheduled_reminders()
