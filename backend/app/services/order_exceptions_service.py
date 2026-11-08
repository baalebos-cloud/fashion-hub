"""Orders that need an admin's eye: read-only, nothing here changes an order.

Rules, all from data already stored:
- tailor_no_reply   customer order paid but not accepted after 24 h
- overdue           customer order accepted/in production past the longest estimated
                    turnaround of its designs (counted from acceptance)
- vendor_no_confirm material order paid but not confirmed by the vendor after 24 h
- vendor_stuck      material order confirmed/processing but not ready for pickup after 72 h
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.timezone import utcnow
from app.models.design import Design
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User

NO_REPLY_AFTER = timedelta(hours=24)
VENDOR_CONFIRM_AFTER = timedelta(hours=24)
VENDOR_STUCK_AFTER = timedelta(hours=72)
SCAN_LIMIT = 500
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

    def _scan(self, order_type: str, statuses: tuple[str, ...]) -> list[Order]:
        return (self.db.query(Order).filter(Order.order_type == order_type, Order.status.in_(statuses))
                .order_by(Order.ordered_at.asc()).limit(SCAN_LIMIT).all())

    def _turnaround_days(self, order_ids: list) -> dict:
        """Longest estimated turnaround (days) among each order's designs."""
        if not order_ids:
            return {}
        rows = (self.db.query(OrderItem.order_id, Design.estimated_turnaround_days)
                .join(Design, Design.id == OrderItem.reference_id)
                .filter(OrderItem.order_id.in_(order_ids), OrderItem.reference_type == "design",
                        Design.estimated_turnaround_days.isnot(None)).all())
        days: dict = {}
        for order_id, value in rows:
            days[order_id] = max(days.get(order_id, 0), int(value))
        return days

    def list(self) -> list[dict]:
        now = utcnow()
        found: list[tuple[Order, str, datetime, str]] = []

        for order in self._scan("customer_order", ("paid",)):
            since = _aware(order.paid_at)
            if since and now - since >= NO_REPLY_AFTER:
                found.append((order, "tailor_no_reply", since, f"Paid {_hours(since, now)} h ago and not accepted yet."))

        making = self._scan("customer_order", ("accepted", "in_production"))
        turnaround = self._turnaround_days([o.id for o in making])
        for order in making:
            accepted = _aware(order.accepted_at)
            days = turnaround.get(order.id)
            if accepted and days:
                due = accepted + timedelta(days=days)
                if now > due:
                    late = (now - due).days
                    found.append((order, "overdue", due,
                                  f"Past the {days}-day estimate by {late} day{'s' if late != 1 else ''}." if late
                                  else f"Past the {days}-day estimate."))

        for order in self._scan("vendor_order", ("paid",)):
            since = _aware(order.paid_at)
            if since and now - since >= VENDOR_CONFIRM_AFTER:
                found.append((order, "vendor_no_confirm", since, f"Paid {_hours(since, now)} h ago; the vendor hasn't confirmed stock."))

        for order in self._scan("vendor_order", ("confirmed", "processing")):
            since = _aware(order.paid_at) or _aware(order.ordered_at)
            if since and now - since >= VENDOR_STUCK_AFTER:
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
