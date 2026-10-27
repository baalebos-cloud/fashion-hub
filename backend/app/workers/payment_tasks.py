"""
Background jobs for payment reconciliation.

Never retry an ambiguous refund automatically: if the provider accepted the
request before a timeout, blindly retrying can send money twice.
"""
from decimal import Decimal

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
    with SessionLocal() as db:
        missing_work = ~exists().where(PaymentOutbox.payment_id == Payment.id)
        references = [row[0] for row in db.query(Payment.provider_reference).filter(or_(
            Payment.status.in_(["initialized", "pending"]),
            (Payment.status == "successful") & missing_work,
        )).order_by(Payment.last_reconciled_at.asc().nulls_first(), Payment.created_at, Payment.id).limit(200)]
    for reference in references:
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


@celery_app.task(name="app.workers.payment_tasks.process_refund_task")
def process_refund_task(refund_id: str):
    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.core.logging import get_logger
    from app.core.timezone import utcnow
    from app.integrations.payments import get_payment_provider
    from app.models.payment import Payment
    from app.models.refund import Refund

    if not settings.REFUND_EXECUTION_ENABLED:
        return "disabled"
    with SessionLocal() as db:
        refund = db.query(Refund).filter(Refund.id == refund_id).with_for_update().first()
        if not refund or refund.status != "approved":
            return "not_approved"
        payment = db.get(Payment, refund.payment_id)
        if not payment or payment.status != "successful" or payment.provider != settings.PAYMENT_PROVIDER:
            refund.status = "manual_review"
            db.commit()
            return "requires_review"
        provider_ref = payment.provider_reference
        amount = Decimal(str(refund.amount))
        # An irrevocable attempt marker is committed BEFORE contacting Paystack.
        # If the call times out, human reconciliation must inspect Paystack.
        refund.status = "processing"
        db.commit()

    try:
        result = get_payment_provider().initiate_refund(
            provider_reference=provider_ref, amount=amount,
        )
        data = result.get("data", result) if isinstance(result, dict) else {}
        status = str(data.get("status", "pending")).lower()
        if status not in {"pending", "processing", "needs-attention", "processed"}:
            status = "manual_review"
        if status == "needs-attention":
            status = "needs_attention"
        provider_refund_id = data.get("id")
        with SessionLocal() as db:
            refund = db.query(Refund).filter(Refund.id == refund_id).with_for_update().first()
            if refund and refund.status == "processing":
                refund.status = status
                if provider_refund_id is not None:
                    refund.provider_refund_reference = str(provider_refund_id)[:128]
                if status == "processed":
                    refund.processed_at = utcnow()
                db.commit()
        return status
    except Exception:
        # Unknown external outcome must not be automatically retried.
        with SessionLocal() as db:
            refund = db.query(Refund).filter(Refund.id == refund_id).with_for_update().first()
            if refund and refund.status == "processing":
                refund.status = "manual_review"
                db.commit()
        get_logger(__name__).warning("refund_requires_provider_reconciliation")
        return "manual_review"


@celery_app.task(name='app.workers.payment_tasks.expire_stock_reservations_task')
def expire_stock_reservations_task():
    from app.core.database import SessionLocal
    from app.services.stock_reservation_service import StockReservationService
    count = 0
    for _ in range(200):
        with SessionLocal() as db:
            if not StockReservationService(db).expire_one():
                break
            count += 1
    return count
