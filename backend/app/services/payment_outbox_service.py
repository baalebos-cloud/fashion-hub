"""Idempotent database effects, retried without depending on broker publication.

A handler, its invoice/notifications, and processed_at commit together. A failed
handler rolls back its savepoint and records a bounded retry delay. No external
network delivery is attempted here; future external effects need their own
provider idempotency keys and acknowledgement/retry lifecycle.
"""
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.timezone import utcnow
from app.models.notification import Notification
from app.models.order import Order
from app.models.payment_outbox import PaymentOutbox
from app.models.referral import Referral
from app.models.user import User
from app.services.invoice_service import InvoiceService

logger = get_logger(__name__)


class PaymentOutboxService:
    def __init__(self, db: Session):
        self.db = db

    def process_one(self, *, payment_id=None) -> bool:
        query = self.db.query(PaymentOutbox).filter(
            PaymentOutbox.processed_at.is_(None), PaymentOutbox.available_at <= utcnow())
        if payment_id is not None:
            query = query.filter(PaymentOutbox.payment_id == payment_id)
        event = (query.order_by(PaymentOutbox.available_at, PaymentOutbox.id)
                 .with_for_update(skip_locked=True).populate_existing().first())
        if not event:
            self.db.commit()
            return False
        try:
            event.attempts += 1
            try:
                with self.db.begin_nested():
                    self._handle(event)
                    self.db.flush()
                event.processed_at = utcnow()
                event.last_error = None
            except Exception as exc:
                event.last_error = type(exc).__name__
                event.available_at = utcnow() + timedelta(seconds=min(3600, 2 ** min(event.attempts, 10)))
                logger.warning("payment_outbox_retry", extra={"outbox_id": str(event.id),
                                                             "error_type": event.last_error})
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def _handle(self, event):
        order = self.db.get(Order, event.payload["order_id"])
        if not order:
            raise ValueError("Outbox order is missing")
        if event.kind == "payment.review":
            admins = self.db.query(User).filter(User.role == "admin", User.is_active.is_(True)).all()
            for admin in admins:
                self._notify(admin.id, "payment.review_required", "Payment needs review",
                             f"Payment for order {order.order_number} arrived in a non-payable order state.", event)
        elif event.kind == "payment.settled":
            InvoiceService(self.db).generate_for_order(order.id, commit=False)
            for recipient in {order.buyer_user_id, order.seller_user_id}:
                self._notify(recipient, "payment.successful", "Payment received",
                             f"Payment for order {order.order_number} was confirmed.", event)
            referral_id = event.payload.get("referral_id")
            if referral_id:
                referral = self.db.get(Referral, referral_id)
                if not referral:
                    raise ValueError("Outbox referral is missing")
                self._notify(referral.referrer_user_id, "referral.qualified", "You earned a referral commission",
                             f"Your referral earned {referral.commission_amount} {referral.commission_currency}.", event)
        else:
            raise ValueError("Unsupported outbox event kind")

    def _notify(self, recipient, event_type, title, body, event):
        self.db.add(Notification(recipient_user_id=recipient, channel="in_app", event_type=event_type,
                                 title=title, body=body, metadata_json={"payment_id": str(event.payment_id)}))
