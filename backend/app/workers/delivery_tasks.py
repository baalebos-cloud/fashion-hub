"""Background jobs for matching delivery requests to available partners and
synchronizing status with external delivery providers."""
from app.core.database import session_scope
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.delivery_tasks.broadcast_delivery_request_task")
def broadcast_delivery_request_task(delivery_request_id: str):
    """Notify nearby available delivery partners (via PostGIS proximity
    query) that a new delivery request is available to accept."""
    with session_scope() as db:
        from app.services.delivery_request_service import DeliveryRequestService
        DeliveryRequestService(db).broadcast_to_nearby_partners(delivery_request_id)


@celery_app.task(name="app.workers.delivery_tasks.sync_external_delivery_status_task")
def sync_external_delivery_status_task(delivery_id: str):
    with session_scope() as db:
        from app.services.delivery_service import DeliveryService
        DeliveryService(db).sync_status_from_provider(delivery_id)


@celery_app.task(name="app.workers.delivery_tasks.notify_dispatch_issue_task")
def notify_dispatch_issue_task(issue_id: str):
    """Persist in-app alerts for this incident, idempotently on Celery retries."""
    from uuid import UUID
    from app.models.delivery_issue import DispatchIssueReport
    from app.models.delivery import Delivery
    from app.models.order import Order
    from app.models.notification import Notification
    from app.models.user import User
    with session_scope() as db:
        issue = db.get(DispatchIssueReport, UUID(issue_id))
        if issue is None:
            return
        delivery = db.get(Delivery, issue.delivery_id)
        order = db.get(Order, delivery.order_id) if delivery else None
        if order is None:
            return
        admins = db.query(User.id).filter(User.role == "admin", User.is_active.is_(True)).all()
        recipients = {order.buyer_user_id, order.seller_user_id} | {row[0] for row in admins}
        for recipient in recipients:
            exists = (db.query(Notification.id)
                .filter(Notification.recipient_user_id == recipient,
                        Notification.event_type == "delivery.exception",
                        Notification.metadata_json.contains({"issue_id": issue_id}))
                .first())
            if exists:
                continue
            db.add(Notification(
                recipient_user_id=recipient, channel="in_app", event_type="delivery.exception",
                title="A delivery issue was reported",
                body="A courier reported an issue affecting an order. Review the delivery details.",
                metadata_json={"issue_id": issue_id, "delivery_id": str(issue.delivery_id)},
            ))
