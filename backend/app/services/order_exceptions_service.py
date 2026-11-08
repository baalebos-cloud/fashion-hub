"""Orders that need an admin's eye: read-only, nothing here changes an order.

Rules, all from data already stored:
- tailor_no_reply   customer order paid but not accepted after 24 h
- overdue           customer order accepted/in production past the longest estimated
                    turnaround of its designs (counted from acceptance)
- vendor_no_confirm material order paid but not confirmed by the vendor after 24 h
- vendor_stuck      material order confirmed/processing but not ready for pickup after 72 h

Each rule is evaluated in SQL and returns its oldest 50; the merged list keeps the oldest 50.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.timezone import utcnow
from app.models.design import Design
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User

NO_REPLY_AFTER = timedelta(hours=24)
VENDOR_CONFIRM_AFTER = timedelta(hours=24)
VENDOR_STUCK_AFTER = timedelta(hours=72)
RETURN_LIMIT = 50


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _hours(since: datetime, now: datetime) -> int:
    return int((now - since).total_seconds() // 3600)


class OrderExceptionsService:
    def __init__(self, db: Session):
        self.db = db

    def _waiting(self, order_type: str, statuses: tuple[str, ...], since_col, older_than: datetime) -> list[Order]:
        """Orders in these statuses whose clock started before `older_than`, oldest first.
        The age test runs in SQL, so only qualifying orders count toward the limit."""
        return (self.db.query(Order)
                .filter(Order.order_type == order_type, Order.status.in_(statuses), since_col.isnot(None), since_col <= older_than)
                .order_by(since_col.asc()).limit(RETURN_LIMIT).all())

    def _overdue(self, now_naive: datetime) -> list[tuple[Order, int, datetime]]:
        """Accepted orders past the longest turnaround estimate of their designs, earliest due first."""
        longest = func.max(Design.estimated_turnaround_days)
        due = Order.accepted_at + func.make_interval(0, 0, 0, longest)
        rows = (self.db.query(Order, longest.label("days"), due.label("due"))
                .join(OrderItem, OrderItem.order_id == Order.id)
                .join(Design, Design.id == OrderItem.reference_id)
                .filter(Order.order_type == "customer_order", Order.status.in_(("accepted", "in_production")),
                        Order.accepted_at.isnot(None), OrderItem.reference_type == "design",
                        Design.estimated_turnaround_days.isnot(None))
                .group_by(Order.id)
                .having(due < now_naive)
                .order_by(due.asc()).limit(RETURN_LIMIT).all())
        return [(order, int(days), _aware(due_at)) for order, days, due_at in rows]

    def list(self) -> list[dict]:
        now = utcnow()
        # Order timestamps are stored as naive UTC; compare like with like.
        now_naive = now.replace(tzinfo=None)
        found: list[tuple[Order, str, datetime, str]] = []

        for order in self._waiting("customer_order", ("paid",), Order.paid_at, now_naive - NO_REPLY_AFTER):
            since = _aware(order.paid_at)
            found.append((order, "tailor_no_reply", since, f"Paid {_hours(since, now)} h ago and not accepted yet."))

        for order, days, due in self._overdue(now_naive):
            late = (now - due).days
            found.append((order, "overdue", due,
                          f"Past the {days}-day estimate by {late} day{'s' if late != 1 else ''}." if late
                          else f"Past the {days}-day estimate."))

        for order in self._waiting("vendor_order", ("paid",), Order.paid_at, now_naive - VENDOR_CONFIRM_AFTER):
            since = _aware(order.paid_at)
            found.append((order, "vendor_no_confirm", since, f"Paid {_hours(since, now)} h ago; the vendor hasn't confirmed stock."))

        started = func.coalesce(Order.paid_at, Order.ordered_at)
        for order in self._waiting("vendor_order", ("confirmed", "processing"), started, now_naive - VENDOR_STUCK_AFTER):
            since = _aware(order.paid_at) or _aware(order.ordered_at)
            found.append((order, "vendor_stuck", since, f"Confirmed but not ready for pickup {_hours(since, now)} h after payment."))

        found.sort(key=lambda row: row[2])
        found = found[:RETURN_LIMIT]
        names = {u.id: u.full_name for u in self.db.query(User).filter(User.id.in_({o.seller_user_id for o, *_ in found})).all()} if found else {}
        return [{
            "kind": kind, "order_id": str(order.id), "order_number": order.order_number, "order_type": order.order_type,
            "status": order.status, "seller_name": names.get(order.seller_user_id),
            "item": order.items[0].name_snapshot if order.items else None,
            "since": since.isoformat(), "message": message,
        } for order, kind, since, message in found]
