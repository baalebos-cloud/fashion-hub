"""Background KYC/KYB provider synchronization (for providers that verify
asynchronously rather than the default manual-review flow)."""
from app.core.database import session_scope
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.kyc_tasks.sync_kyc_status_task")
def sync_kyc_status_task(kyc_verification_id: str):
    with session_scope() as db:
        from app.services.kyc_service import KYCService
        KYCService(db).sync_status_from_provider(kyc_verification_id)


@celery_app.task(name="app.workers.kyc_tasks.sync_kyb_status_task")
def sync_kyb_status_task(kyb_verification_id: str):
    with session_scope() as db:
        from app.services.kyb_service import KYBService
        KYBService(db).sync_status_from_provider(kyb_verification_id)
