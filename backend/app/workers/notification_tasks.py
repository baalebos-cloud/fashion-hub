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


@celery_app.task(name="app.workers.notification_tasks.notify_referral_qualified_task")
def notify_referral_qualified_task(referral_id: str):
    with session_scope() as db:
        from app.services.notification_service import NotificationService
        NotificationService(db).notify_referral_qualified(referral_id=referral_id)


@celery_app.task(name="app.workers.notification_tasks.send_scheduled_reminders_task")
def send_scheduled_reminders_task():
    with session_scope() as db:
        from app.services.notification_service import NotificationService
        NotificationService(db).send_scheduled_reminders()


@celery_app.task(name="app.workers.notification_tasks.sync_interaction_history_task")
def sync_interaction_history_task():
    """Copy cart adds, favourites and purchases into the recommendations activity table."""
    from app.core.database import session_scope
    from app.services.interaction_service import sync_history
    with session_scope() as db:
        return sync_history(db)


@celery_app.task(name="app.workers.notification_tasks.rebuild_item_similarities_task")
def rebuild_item_similarities_task():
    """Rebuild learned related items from shopping activity."""
    from app.core.database import session_scope
    from app.services.similarity_service import rebuild
    with session_scope() as db:
        return rebuild(db)


@celery_app.task(name="app.workers.notification_tasks.purge_interactions_task")
def purge_interactions_task():
    """Delete shopping activity older than INTERACTION_RETENTION_DAYS."""
    from app.core.database import session_scope
    from app.services.interaction_service import purge_expired
    with session_scope() as db:
        return purge_expired(db)


@celery_app.task(name="app.workers.notification_tasks.purge_activity_logs_task")
def purge_activity_logs_task():
    """Delete activity-log entries older than ACTIVITY_LOG_RETENTION_DAYS."""
    from app.core.database import session_scope
    from app.services.activity_service import purge_expired
    with session_scope() as db:
        return purge_expired(db)
