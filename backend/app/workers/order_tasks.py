"""Bounded, non-financial Saga monitoring jobs.

Never automatically refund or transfer value. Ambiguous provider outcomes
always go to a review queue; retry only the internal audit/recovery work.
"""
from datetime import timedelta
import json

from redis import Redis
from sqlalchemy import and_, exists

from app.core.config import settings
from app.core.database import session_scope
from app.core.timezone import utcnow
from app.models.order import Order
from app.models.saga import SagaStepLog
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.order_tasks.sweep_stale_saga_orders",
                 bind=True, max_retries=5)
def sweep_stale_saga_orders(self):
    if settings.APP_ENV == "production" or settings.PAYMENTS_ENABLED:
        return "disabled"
    try:
        cutoff = utcnow() - timedelta(hours=48)
        with session_scope() as db:
            already_reviewed = exists().where(and_(
                SagaStepLog.order_id == Order.id,
                SagaStepLog.step_name == "REVIEW_REQUIRED",
            ))
            rows = (
                db.query(Order)
                .filter(Order.order_type == "customer_order",
                        Order.status == "paid",
                        Order.created_at < cutoff,
                        ~already_reviewed)
                .order_by(Order.created_at, Order.id)
                .limit(100)
                .with_for_update(skip_locked=True)
                .all()
            )
            for order in rows:
                db.add(SagaStepLog(
                    order_id=order.id, step_name="REVIEW_REQUIRED",
                    status="completed", error_reason="Tailor acceptance SLA expired. Manual financial review required.",
                    payload={"reason": "tailor_timeout", "sandbox": True},
                ))
            return len(rows)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            try:
                redis = Redis.from_url(settings.REDIS_URL, socket_timeout=2)
                redis.lpush("seam:saga:dead-letter", json.dumps({
                    "task": "sweep_stale_saga_orders",
                    "exception_type": type(exc).__name__,
                    "timestamp": utcnow().isoformat(),
                }))
                redis.expire("seam:saga:dead-letter", 60 * 60 * 24 * 30)
            except Exception:
                pass  # Observability fallback; Celery still records failure.
            raise
        raise self.retry(exc=exc, countdown=min(30 * (2 ** self.request.retries), 1800))


@celery_app.task(name="app.workers.order_tasks.retry_courier_dispatch",
                 bind=True, max_retries=5)
def retry_courier_dispatch(self, order_id: str):
    """Record a retry requirement; actual assignment must use authorized dispatch."""
    if settings.APP_ENV == "production" or settings.PAYMENTS_ENABLED:
        return "disabled"
    from app.core.exceptions import NotFoundError
    from app.models.order import Order
    with session_scope() as db:
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order:
            raise NotFoundError("Order not found.")
        if order.status not in {"ready_for_delivery", "shipped", "out_for_delivery"}:
            return "not_dispatchable"
        db.add(SagaStepLog(
            order_id=order.id,
            step_name="COURIER_REASSIGNMENT_REQUIRED",
            status="review_required",
            error_reason="Dispatch failed or courier unavailable; manual reassignment required.",
            payload={"sandbox": True, "retry_count": self.request.retries},
        ))
        return "review_required"
