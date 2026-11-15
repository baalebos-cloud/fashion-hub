"""User-scoped dashboard counts derived from orders, never static placeholders."""
from sqlalchemy.orm import Session

from app.models.order import Order

TERMINAL = {"cancelled", "completed", "received"}


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def summary(self, user):
        if user.role == "delivery_partner":
            # A rider's dashboard is about their jobs, not orders they've bought.
            from app.services.rider_work_service import RiderWorkService
            return RiderWorkService(self.db).dashboard_cards(user)
        seller = user.role in {"tailor", "designer", "vendor"}
        scope = self.db.query(Order)
        if user.role == "admin":
            label = "Platform orders"
        elif seller:
            scope = scope.filter(Order.seller_user_id == user.id)
            label = "Sales orders"
        else:
            scope = scope.filter(Order.buyer_user_id == user.id)
            label = "My orders"
        total = scope.count()
        active = scope.filter(~Order.status.in_(TERMINAL)).count()
        completed = scope.filter(Order.status.in_({"received", "completed"})).count()
        cancelled = scope.filter(Order.status == "cancelled").count()
        return [
            {"kind": "orders", "label": label, "value": total},
            {"kind": "active", "label": "In progress", "value": active},
            {"kind": "completed", "label": "Completed", "value": completed},
            {"kind": "cancelled", "label": "Cancelled", "value": cancelled},
        ]
