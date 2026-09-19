"""
Computes and records what a professional/vendor actually nets on an
order, per the platform's 15% commission rate (PLATFORM_COMMISSION_RATE).

CRITICAL invariant this service exists to protect: the customer's invoice
(invoice_service.py) is built from Order.total_amount alone -- the price
the professional/vendor quoted, already inclusive of their cut of the
commission by mutual negotiation at onboarding. This service NEVER
touches Order.total_amount and is NEVER read by anything customer-facing
(see api/v1/invoices.py, which has no Payout import). The commission is
invisible to the customer by construction: there is no code path from a
customer-facing endpoint into this table, not a permission check that
could be misconfigured.
"""
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.order import Order
from app.models.payout import Payout


class PayoutService:
    def __init__(self, db: Session):
        self.db = db

    def create_for_order(self, order: Order) -> Payout:
        existing = self.db.query(Payout).filter(Payout.order_id == order.id).first()
        if existing:
            return existing  # idempotent, same reasoning as payment webhook de-dup

        gross = float(order.total_amount)
        rate = settings.PLATFORM_COMMISSION_RATE
        commission = round(gross * rate, 2)
        net = round(gross - commission, 2)

        payout = Payout(
            order_id=order.id,
            seller_user_id=order.seller_user_id,
            gross_amount=gross,
            commission_rate=rate,
            commission_amount=commission,
            net_amount=net,
            currency=order.currency,
            status="pending",
        )
        self.db.add(payout)
        self.db.commit()
        self.db.refresh(payout)
        return payout

    def list_for_seller(self, seller_user_id, *, offset: int = 0, limit: int = 20) -> list[Payout]:
        return (
            self.db.query(Payout)
            .filter(Payout.seller_user_id == seller_user_id)
            .order_by(Payout.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
