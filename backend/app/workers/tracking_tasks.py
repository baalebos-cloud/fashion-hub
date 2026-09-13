"""
Background jobs for delivery tracking, including detection of the
"delivery GPS temporarily stops updating" edge case: if a delivery is
IN_TRANSIT/OUT_FOR_DELIVERY but its last_ping_at is older than a threshold,
flag it and notify support/the customer rather than silently going stale.
"""
from datetime import timedelta

from app.core.database import session_scope
from app.core.timezone import utcnow
from app.workers.celery_app import celery_app

STALE_THRESHOLD_MINUTES = 15


@celery_app.task(name="app.workers.tracking_tasks.check_stale_tracking_task")
def check_stale_tracking_task():
    from app.models.delivery_tracking import DeliveryTracking

    cutoff = utcnow() - timedelta(minutes=STALE_THRESHOLD_MINUTES)
    with session_scope() as db:
        stale = (
            db.query(DeliveryTracking)
            .filter(
                DeliveryTracking.current_status.in_(["picked_up", "in_transit", "out_for_delivery"]),
                DeliveryTracking.last_ping_at < cutoff,
            )
            .all()
        )
        for tracking in stale:
            from app.workers.notification_tasks import notify_delivery_tracking_stale_task
            notify_delivery_tracking_stale_task.delay(delivery_id=str(tracking.delivery_id))
