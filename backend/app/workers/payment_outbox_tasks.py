"""A periodic database poll recovers work even after broker outages."""
from app.core.database import SessionLocal
from app.services.payment_outbox_service import PaymentOutboxService
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.payment_outbox_tasks.drain_payment_outbox")
def drain_payment_outbox(limit: int = 100):
    processed = 0
    with SessionLocal() as db:
        service = PaymentOutboxService(db)
        for _ in range(min(max(limit, 1), 1000)):
            if not service.process_one():
                break
            processed += 1
    return processed
