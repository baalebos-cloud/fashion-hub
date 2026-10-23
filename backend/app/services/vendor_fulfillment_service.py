"""Atomic progression of paid material orders by the owning vendor."""
from sqlalchemy.orm import Session
from app.core.constants import VENDOR_ORDER_TRANSITIONS, VendorOrderStatus
from app.core.exceptions import ConflictError, ForbiddenError, InvalidStateTransitionError, NotFoundError
from app.core.timezone import utcnow
from app.models.order_timeline import OrderTimelineEntry
from app.repositories.order_repository import OrderRepository

SELF_SERVICE = {
    VendorOrderStatus.CONFIRMED: "accepted_at",
    VendorOrderStatus.PROCESSING: "production_started_at",
    VendorOrderStatus.READY_FOR_PICKUP: "ready_at",
}


class VendorFulfillmentService:
    def __init__(self, db: Session):
        self.db = db
        self.orders = OrderRepository(db)

    def transition(self, *, order_id, actor, target_status: str, note: str | None = None):
        order = self.orders.get_by_id_for_update(order_id)
        if not order:
            raise NotFoundError("Order not found.")
        if order.order_type != "vendor_order":
            raise ConflictError("Only material orders support this workflow.")
        if actor.role != "vendor" or str(actor.id) != str(order.seller_user_id):
            raise ForbiddenError("Only this order's vendor may update fulfillment.")
        target = VendorOrderStatus(target_status)
        if target not in SELF_SERVICE:
            raise ForbiddenError("This transition is not available to vendors.")
        current = VendorOrderStatus(order.status)
        if target not in VENDOR_ORDER_TRANSITIONS.get(current, []):
            raise InvalidStateTransitionError(
                f"Cannot transition material order from '{current.value}' to '{target.value}'."
            )
        order.status = target.value
        setattr(order, SELF_SERVICE[target], utcnow())
        self.db.add(OrderTimelineEntry(order_id=order.id, from_status=current.value,
                                       to_status=target.value, actor_user_id=actor.id, note=note))
        self.db.commit()
        self.db.refresh(order)
        return order
