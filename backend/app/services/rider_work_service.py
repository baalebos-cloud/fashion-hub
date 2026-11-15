"""A rider's own finished jobs and what they earned: the History and Earnings pages and the
rider dashboard. Only deliveries assigned to this rider; amounts are the agreed delivery fares."""
from datetime import timedelta, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.timezone import utcnow
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner

ACTIVE = ("assigned", "picked_up", "in_transit", "out_for_delivery")
FINISHED = ("delivered", "failed", "cancelled")
LAGOS = timezone(timedelta(hours=1))  # Nigeria has no daylight saving


def _utc(moment):
    # Timezone-aware on purpose: Postgres then compares it with the stored times correctly
    # whatever the database session's timezone is.
    return moment.astimezone(timezone.utc)


class RiderWorkService:
    def __init__(self, db: Session):
        self.db = db

    def _mine(self, user):
        return (self.db.query(Delivery).join(DeliveryPartner, Delivery.delivery_partner_id == DeliveryPartner.id)
                .filter(DeliveryPartner.user_id == user.id))

    def history(self, user, *, offset: int = 0, limit: int = 20):
        return (self._mine(user).filter(Delivery.status.in_(FINISHED))
                .order_by(func.coalesce(Delivery.delivered_at, Delivery.updated_at).desc(), Delivery.id)
                .offset(offset).limit(limit).all())

    def _period_starts(self):
        now = utcnow().astimezone(LAGOS)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week = today - timedelta(days=today.weekday())  # Monday
        month = today.replace(day=1)
        return {"today": today, "week": week, "month": month}

    def earnings(self, user) -> dict:
        delivered = self._mine(user).filter(Delivery.status == "delivered", Delivery.delivered_at.isnot(None))
        result = {"currency": "NGN"}
        for name, start in self._period_starts().items():
            rows = delivered.filter(Delivery.delivered_at >= _utc(start))
            result[name] = {"amount": float(rows.with_entities(func.coalesce(func.sum(Delivery.delivery_fee), 0)).scalar() or 0),
                            "deliveries": rows.count()}
        total = delivered.with_entities(func.coalesce(func.sum(Delivery.delivery_fee), 0), func.count(Delivery.id)).one()
        result["all_time"] = {"amount": float(Decimal(total[0] or 0)), "deliveries": int(total[1] or 0)}
        return result

    def dashboard_cards(self, user) -> list[dict]:
        earned = self.earnings(user)
        partner = self.db.query(DeliveryPartner).filter_by(user_id=user.id).first()
        rating = float(partner.average_rating or 0) if partner else 0.0
        return [
            {"kind": "active", "label": "Current jobs", "value": self._mine(user).filter(Delivery.status.in_(ACTIVE)).count()},
            {"kind": "delivered_today", "label": "Delivered today", "value": earned["today"]["deliveries"]},
            {"kind": "earned_week", "label": "Earned this week", "value": f"₦{earned['week']['amount']:,.0f}"},
            {"kind": "rating", "label": "Rating", "value": f"{rating:.1f} ★" if rating else "New"},
        ]
