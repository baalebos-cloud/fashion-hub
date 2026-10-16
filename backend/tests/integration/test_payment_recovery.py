"""Real Postgres rollback, duplicate, recovery, and concurrency regressions."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier, Event
from unittest.mock import MagicMock, patch
import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import PaymentError
from app.core.timezone import utcnow
from app.integrations.payments.base import VerifyPaymentResult
from app.models.audit_log import AuditLog
from app.models.invoice import Invoice
from app.models.notification import Notification
from app.models.order import Order
from app.models.order_timeline import OrderTimelineEntry
from app.models.payment import Payment
from app.models.payment_outbox import PaymentOutbox
from app.models.payment_transaction import PaymentTransaction
from app.models.payout import Payout
from app.models.referral import Referral
from app.models.user import User
from app.services.invoice_service import InvoiceService
from app.services.payment_outbox_service import PaymentOutboxService
from app.services.payment_service import PaymentService
from app.services.payout_service import PayoutService


def seed(db, *, status="pending", vendor=False):
    users = [User(id=uuid.uuid4(), email=f"{uuid.uuid4()}@example.com", full_name="Test",
                  role=role, hashed_password="not-used-by-this-test") for role in ["customer", "vendor" if vendor else "tailor", "customer"]]
    db.add_all(users)
    db.flush()
    order = Order(id=uuid.uuid4(), order_number="TEST-" + uuid.uuid4().hex[:16],
                  order_type="vendor_order" if vendor else "customer_order", buyer_user_id=users[0].id,
                  seller_user_id=users[1].id, status=status, subtotal=Decimal("100.01"),
                  total_amount=Decimal("100.01"), currency="NGN", ordered_at=utcnow())
    db.add(order)
    db.flush()
    payment = Payment(id=uuid.uuid4(), order_id=order.id, provider="paystack", status="initialized",
                      provider_reference="test-" + uuid.uuid4().hex, amount=order.total_amount, currency="NGN")
    referral = Referral(id=uuid.uuid4(), referrer_user_id=users[2].id, referred_user_id=users[0].id,
                        referral_code_used="TEST", status="pending")
    db.add_all([payment, referral])
    db.commit()
    return payment.id, order.id, referral.id


@pytest.fixture()
def provider(monkeypatch):
    provider = MagicMock()
    provider.verify_webhook_signature.return_value = True
    monkeypatch.setattr("app.services.payment_service.get_payment_provider", lambda: provider)
    return provider


def configure(provider, payment, status="successful", amount=None):
    result = VerifyPaymentResult(provider_reference=payment.provider_reference, status=status,
                                 amount=amount if amount is not None else payment.amount,
                                 currency=payment.currency, paid_at=None, raw_response={})
    provider.verify_payment.return_value = result
    return result


def webhook(service, payment, event="settlement"):
    return service.process_webhook(payload=b"signed-body", signature_header="signature",
                                   provider_event_id=event, event_type="charge.success",
                                   provider_reference=payment.provider_reference, amount=payment.amount)


def count(db, model, **filters):
    return db.query(model).filter_by(**filters).count()


@pytest.mark.parametrize("failure", ["payout", "commit"])
def test_failed_settlement_rolls_back_every_financial_effect_and_retries(db, provider, failure):
    payment_id, order_id, referral_id = seed(db)
    payment = db.get(Payment, payment_id)
    configure(provider, payment)
    target = patch.object(PayoutService, "create_for_order", side_effect=RuntimeError("injected")) if failure == "payout" else patch.object(db, "commit", side_effect=RuntimeError("injected"))
    with target, pytest.raises(RuntimeError, match="injected"):
        webhook(PaymentService(db), payment)
    assert db.get(Payment, payment_id).status == "initialized"
    assert db.get(Order, order_id).status == "pending"
    assert db.get(Referral, referral_id).status == "pending"
    assert count(db, Payout, order_id=order_id) == 0
    assert count(db, PaymentOutbox, payment_id=payment_id) == 0
    assert count(db, PaymentTransaction, payment_id=payment_id) == 0
    assert count(db, OrderTimelineEntry, order_id=order_id) == 0
    webhook(PaymentService(db), db.get(Payment, payment_id))
    assert db.get(Order, order_id).status == "paid"
    assert count(db, Payout, order_id=order_id) == 1
    assert count(db, PaymentOutbox, payment_id=payment_id) == 1


def test_duplicate_processed_event_needs_neither_redis_nor_provider(db, provider):
    payment_id, order_id, _ = seed(db)
    payment = db.get(Payment, payment_id)
    configure(provider, payment)
    with patch("app.core.redis.acquire_idempotency_lock", side_effect=RuntimeError("Redis down")), patch("app.workers.invoice_tasks.generate_invoice_for_order_task.delay", side_effect=RuntimeError("Broker down")):
        webhook(PaymentService(db), payment)
    provider.verify_payment.side_effect = RuntimeError("Provider temporarily unavailable")
    assert webhook(PaymentService(db), payment) is None
    assert count(db, Payout, order_id=order_id) == 1
    assert count(db, PaymentTransaction, payment_id=payment_id) == 1


def test_unprocessed_legacy_event_and_partial_payment_are_repaired(db, provider):
    payment_id, order_id, _ = seed(db)
    payment = db.get(Payment, payment_id)
    payment.status = "successful"
    db.add(PaymentTransaction(payment_id=payment_id, provider="paystack", provider_event_id="settlement",
                              event_type="charge.success", amount=payment.amount, raw_payload={}, processed=False))
    db.commit()
    configure(provider, payment)
    webhook(PaymentService(db), payment)
    assert db.get(Order, order_id).status == "paid"
    assert db.query(PaymentTransaction).filter_by(payment_id=payment_id).one().processed is True
    assert count(db, Payout, order_id=order_id) == 1
    assert count(db, PaymentOutbox, payment_id=payment_id) == 1


def test_failed_outbox_rolls_back_invoice_and_notifications_then_recovers_once(db, provider):
    payment_id, order_id, _ = seed(db)
    payment = db.get(Payment, payment_id)
    configure(provider, payment)
    webhook(PaymentService(db), payment)
    service = PaymentOutboxService(db)
    with patch.object(service, "_notify", side_effect=RuntimeError("injected")):
        assert service.process_one(payment_id=payment_id)
    event = db.query(PaymentOutbox).filter_by(payment_id=payment_id).one()
    assert event.processed_at is None and event.attempts == 1 and event.last_error == "RuntimeError"
    assert count(db, Invoice, order_id=order_id) == 0
    assert db.get(Payment, payment_id).status == "successful"
    event.available_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert service.process_one(payment_id=payment_id)
    assert not service.process_one(payment_id=payment_id)
    assert count(db, Invoice, order_id=order_id) == 1
    assert db.query(Notification).filter(Notification.metadata_json["payment_id"].astext == str(payment_id)).count() == 3
    assert db.query(PaymentOutbox).filter_by(payment_id=payment_id).one().processed_at is not None


def test_cancelled_order_records_payment_for_review_without_seller_payout(db, provider):
    payment_id, order_id, _ = seed(db, status="cancelled")
    payment = db.get(Payment, payment_id)
    configure(provider, payment)
    webhook(PaymentService(db), payment)
    assert payment.status == "successful"
    assert db.get(Order, order_id).status == "cancelled"
    assert count(db, Payout, order_id=order_id) == 0
    assert count(db, AuditLog, resource_id=payment_id, action="payment.review_required") == 1
    assert db.query(PaymentOutbox).filter_by(payment_id=payment_id).one().kind == "payment.review"


def test_vendor_checkout_payment_reaches_paid(db, provider):
    payment_id, order_id, _ = seed(db, status="checkout", vendor=True)
    payment = db.get(Payment, payment_id)
    configure(provider, payment)
    webhook(PaymentService(db), payment)
    assert db.get(Order, order_id).status == "paid"
    assert db.query(OrderTimelineEntry).filter_by(order_id=order_id).one().from_status == "checkout"


def test_settlement_rejects_underpayment_before_writing(db, provider):
    payment_id, _, _ = seed(db)
    payment = db.get(Payment, payment_id)
    configure(provider, payment, amount=Decimal("0.01"))
    with pytest.raises(PaymentError, match="amount"):
        webhook(PaymentService(db), payment)
    assert count(db, PaymentOutbox, payment_id=payment_id) == 0
    assert payment.status == "initialized"


def test_late_failed_event_cannot_reverse_success(db, provider):
    payment_id, order_id, _ = seed(db)
    payment = db.get(Payment, payment_id)
    configure(provider, payment)
    webhook(PaymentService(db), payment)
    configure(provider, payment, status="failed")
    PaymentService(db).process_webhook(payload=b"signed", signature_header="ok", provider_event_id="late-failure",
                                       event_type="charge.failed", provider_reference=payment.provider_reference, amount=payment.amount)
    assert payment.status == "successful"
    assert db.get(Order, order_id).status == "paid"
    assert count(db, Payout, order_id=order_id) == 1


def test_callback_and_webhook_concurrently_settle_only_once(engine, provider):
    with Session(engine) as db:
        payment_id, order_id, _ = seed(db)
        payment = db.get(Payment, payment_id)
        reference = payment.provider_reference
        verification = configure(provider, payment)
    barrier = Barrier(2)

    def verify(_):
        barrier.wait(timeout=10)
        return verification

    provider.verify_payment.side_effect = verify

    def settle(is_callback):
        with Session(engine) as db:
            service = PaymentService(db)
            if is_callback:
                service.verify_and_confirm(reference)
            else:
                webhook(service, db.get(Payment, payment_id), event="concurrent-" + reference)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(settle, value) for value in (True, False)]
        for future in futures:
            future.result(timeout=20)
    with Session(engine) as db:
        assert count(db, Payout, order_id=order_id) == 1
        assert count(db, PaymentOutbox, payment_id=payment_id) == 1
        assert count(db, OrderTimelineEntry, order_id=order_id, to_status="paid") == 1
        assert count(db, PaymentTransaction, payment_id=payment_id, processed=True) == 2


def test_two_outbox_workers_do_not_duplicate_invoice_or_notifications(engine, provider):
    with Session(engine) as db:
        payment_id, order_id, _ = seed(db)
        payment = db.get(Payment, payment_id)
        configure(provider, payment)
        webhook(PaymentService(db), payment, event="worker-" + str(payment_id))
    started, release = Event(), Event()

    def first_worker():
        with Session(engine) as db:
            service = PaymentOutboxService(db)
            original = service._handle

            def pause(event):
                started.set()
                assert release.wait(timeout=10)
                original(event)

            service._handle = pause
            return service.process_one(payment_id=payment_id)

    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(first_worker)
        try:
            assert started.wait(timeout=10)
            with Session(engine) as db:
                assert not PaymentOutboxService(db).process_one(payment_id=payment_id)
        finally:
            release.set()
        assert first.result(timeout=20)
    with Session(engine) as db:
        assert count(db, Invoice, order_id=order_id) == 1
        assert db.query(Notification).filter(Notification.metadata_json["payment_id"].astext == str(payment_id)).count() == 3
        invoice = InvoiceService(db).generate_for_order(order_id)
        assert invoice.id is not None
        assert count(db, Invoice, order_id=order_id) == 1


def test_provider_event_cannot_be_reassigned_to_another_payment(db, provider):
    from app.core.exceptions import ConflictError
    first_id, _, _ = seed(db)
    first = db.get(Payment, first_id)
    configure(provider, first)
    webhook(PaymentService(db), first)
    second_id, second_order_id, _ = seed(db)
    second = db.get(Payment, second_id)
    configure(provider, second)
    with pytest.raises(ConflictError):
        webhook(PaymentService(db), second)
    assert second.status == "initialized"
    assert count(db, Payout, order_id=second_order_id) == 0


def test_financial_amounts_use_exact_decimal_rounding(db, provider):
    payment_id, order_id, referral_id = seed(db)
    payment = db.get(Payment, payment_id)
    configure(provider, payment)
    webhook(PaymentService(db), payment)
    payout = db.query(Payout).filter_by(order_id=order_id).one()
    assert payout.gross_amount == Decimal("100.01")
    assert payout.commission_amount == Decimal("15.00")
    assert payout.net_amount == Decimal("85.01")
    assert db.get(Referral, referral_id).commission_amount == Decimal("3.00")


def test_reconciler_repairs_legacy_payment_after_another_reference_fails(engine, provider, monkeypatch):
    from app.workers.payment_tasks import reconcile_pending_payments_task
    with Session(engine) as db:
        failed_id, _, _ = seed(db)
        legacy_id, legacy_order_id, _ = seed(db)
        failed = db.get(Payment, failed_id)
        legacy = db.get(Payment, legacy_id)
        failed_reference = failed.provider_reference
        legacy_reference = legacy.provider_reference
        legacy.status = "successful"  # committed by the old implementation, without effects
        verification = configure(provider, legacy)
        db.commit()

    def verify(reference):
        if reference == failed_reference:
            raise RuntimeError("Provider temporarily unavailable")
        assert reference == legacy_reference
        return verification

    provider.verify_payment.side_effect = verify
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: Session(engine))
    reconcile_pending_payments_task.run()
    with Session(engine) as db:
        assert db.get(Payment, failed_id).status == "initialized"
        assert db.get(Payment, failed_id).last_reconciled_at is not None
        assert db.get(Payment, legacy_id).last_reconciled_at is not None
        assert db.get(Order, legacy_order_id).status == "paid"
        assert count(db, Payout, order_id=legacy_order_id) == 1
        assert count(db, PaymentOutbox, payment_id=legacy_id) == 1
