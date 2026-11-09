"""Every few minutes: send payouts that are due, and check transfers Paystack hasn't answered yet."""
from app.core.database import SessionLocal
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.payout_tasks.release_payouts_task")
def release_payouts_task() -> dict:
    from app.services.payout_release_service import PayoutReleaseService
    db = SessionLocal()
    try:
        service = PayoutReleaseService(db)
        counts = service.release_ready()
        counts["checked"] = service.reconcile_processing()
        return counts
    finally:
        db.close()
