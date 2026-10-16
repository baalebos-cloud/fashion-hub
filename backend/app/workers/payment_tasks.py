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
    from sqlalchemy import exists, or_
    from app.core.database import SessionLocal
    from app.core.logging import get_logger
    from app.core.timezone import utcnow
    from app.models.payment import Payment
    from app.models.payment_outbox import PaymentOutbox
    from app.services.payment_service import PaymentService

    logger = get_logger(__name__)
    # Include successful legacy payments with no durable work record so a
    # previous partial commit can be completed after upgrading.
    with SessionLocal() as db:
        missing_work = ~exists().where(PaymentOutbox.payment_id == Payment.id)
        references = [row[0] for row in db.query(Payment.provider_reference).filter(or_(
            Payment.status.in_(["initialized", "pending"]),
            (Payment.status == "successful") & missing_work,
        )).order_by(Payment.last_reconciled_at.asc().nulls_first(), Payment.created_at, Payment.id).limit(200)]
    for reference in references:
        # One failed provider or database transaction cannot poison the next.
        with SessionLocal() as db:
            try:
                PaymentService(db).verify_and_confirm(reference)
            except Exception as exc:
                db.rollback()
                logger.warning("payment_reconciliation_failed", extra={
                    "provider_reference": reference, "error_type": type(exc).__name__,
                })
            finally:
                db.query(Payment).filter(Payment.provider_reference == reference).update(
                    {"last_reconciled_at": utcnow()}, synchronize_session=False,
                )
                db.commit()


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
