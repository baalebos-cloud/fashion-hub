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
