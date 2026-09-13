"""
Background jobs for payment reconciliation.

`reconcile_pending_payments_task` is the backstop for the "webhook arrives
late / never arrives" edge case: it periodically re-verifies any payment
still in a non-terminal state directly against the provider, rather than
waiting indefinitely for a webhook.
"""
from app.core.database import session_scope
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.payment_tasks.reconcile_pending_payments_task")
def reconcile_pending_payments_task():
    from app.models.payment import Payment
    from app.services.payment_service import PaymentService

    with session_scope() as db:
        pending = db.query(Payment).filter(Payment.status.in_(["initialized", "pending"])).limit(200).all()
        service = PaymentService(db)
        for payment in pending:
            try:
                service.verify_and_confirm(payment.provider_reference)
            except Exception:  # noqa: BLE001 - keep reconciling other payments even if one fails
                continue


@celery_app.task(name="app.workers.payment_tasks.process_refund_task", bind=True, max_retries=3)
def process_refund_task(self, refund_id: str):
    from app.core.exceptions import ExternalProviderError
    from app.models.refund import Refund

    with session_scope() as db:
        refund = db.get(Refund, refund_id)
        if not refund:
            return
        from app.integrations.payments import get_payment_provider
        provider = get_payment_provider()
        try:
            provider.initiate_refund(provider_reference=str(refund.payment_id), amount=float(refund.amount))
            refund.status = "processed"
        except ExternalProviderError as exc:
            raise self.retry(exc=exc, countdown=60)
        db.commit()
