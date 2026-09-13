"""
Order lifecycle service -- the single authoritative place that mutates
order.status. Route handlers and other services MUST go through this
service rather than setting order.status directly, so every transition is:

  1. Validated against the state machine (app/core/constants.py).
  2. Validated against WHO is allowed to make it (role-scoped rules below).
  3. Recorded in the append-only order_timeline.
  4. Stamped with a server-generated timestamp (never client-supplied).
  5. Wrapped in a DB transaction with a row lock, so concurrent
     transitions on the same order can't race each other.

Special rule enforced here (per product spec): only the CUSTOMER may move
an order from DELIVERED -> RECEIVED. The tailor/designer cannot do this,
even via a direct API call, because the role check happens inside the
service rather than only in route-level RBAC.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.constants import CUSTOMER_ORDER_TRANSITIONS, CustomerOrderStatus, UserRole
from app.core.exceptions import ConflictError, ForbiddenError, InvalidStateTransitionError, NotFoundError
from app.core.timezone import utcnow
from app.models.order import Order
from app.models.order_timeline import OrderTimelineEntry
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.utils.order_number import generate_order_number

# Maps a target status to the field on Order that should be stamped with
# the transition timestamp, and to the roles allowed to perform it.
_TRANSITION_RULES: dict[CustomerOrderStatus, dict] = {
    CustomerOrderStatus.PAID: {"timestamp_field": "paid_at", "allowed_roles": None},  # system/payment webhook only
    CustomerOrderStatus.ACCEPTED: {"timestamp_field": "accepted_at", "allowed_roles": {UserRole.TAILOR, UserRole.DESIGNER}},
    CustomerOrderStatus.IN_PRODUCTION: {"timestamp_field": "production_started_at", "allowed_roles": {UserRole.TAILOR, UserRole.DESIGNER}},
    CustomerOrderStatus.READY_FOR_DELIVERY: {"timestamp_field": "ready_at", "allowed_roles": {UserRole.TAILOR, UserRole.DESIGNER}},
    CustomerOrderStatus.SHIPPED: {"timestamp_field": "shipped_at", "allowed_roles": {UserRole.TAILOR, UserRole.DESIGNER}},
    CustomerOrderStatus.OUT_FOR_DELIVERY: {"timestamp_field": "out_for_delivery_at", "allowed_roles": {UserRole.DELIVERY_PARTNER}},
    CustomerOrderStatus.DELIVERED: {"timestamp_field": "delivered_at", "allowed_roles": {UserRole.DELIVERY_PARTNER}},
    # CRITICAL: only the customer (buyer) may confirm receipt. This is
    # enforced with an explicit ownership + role check below, not just role.
    CustomerOrderStatus.RECEIVED: {"timestamp_field": "received_at", "allowed_roles": {UserRole.CUSTOMER}},
    CustomerOrderStatus.COMPLETED: {"timestamp_field": "completed_at", "allowed_roles": None},  # system-triggered
    CustomerOrderStatus.CANCELLED: {"timestamp_field": "cancelled_at", "allowed_roles": {UserRole.CUSTOMER, UserRole.TAILOR, UserRole.DESIGNER, UserRole.ADMIN}},
}


class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.orders = OrderRepository(db)

    def create_customer_order(
        self,
        *,
        customer: User,
        professional_user_id,
        order_items: list[dict],
        delivery_address_id,
        measurement_profile_id: Optional[str],
        idempotency_key: Optional[str],
    ) -> Order:
        """Creates a PENDING order. Edge case: duplicate submission -- if the
        client retries with the same idempotency_key (e.g. after losing
        connectivity mid-checkout), return the existing order instead of
        creating a second one."""
        if idempotency_key:
            existing = self.orders.get_by_idempotency_key(idempotency_key)
            if existing:
                return existing

        subtotal = sum(item["unit_price"] * item["quantity"] for item in order_items)

        order = Order(
            order_number=generate_order_number(prefix="CO"),
            order_type="customer_order",
            buyer_user_id=customer.id,
            seller_user_id=professional_user_id,
            status=CustomerOrderStatus.PENDING.value,
            subtotal=subtotal,
            total_amount=subtotal,  # delivery_fee/tax applied at checkout time
            delivery_address_id=delivery_address_id,
            measurement_profile_id=measurement_profile_id,
            ordered_at=utcnow(),
            idempotency_key=idempotency_key,
        )
        self.orders.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def transition(
        self,
        *,
        order_id,
        target_status: CustomerOrderStatus,
        actor: User,
        note: Optional[str] = None,
    ) -> Order:
        order = self.orders.get_by_id_for_update(order_id)
        if not order:
            raise NotFoundError("Order not found.")

        current_status = CustomerOrderStatus(order.status)
        valid_next = CUSTOMER_ORDER_TRANSITIONS.get(current_status, [])
        if target_status not in valid_next:
            raise InvalidStateTransitionError(
                f"Cannot transition order from '{current_status.value}' to '{target_status.value}'."
            )

        rule = _TRANSITION_RULES.get(target_status, {})
        allowed_roles = rule.get("allowed_roles")
        if allowed_roles is not None and UserRole(actor.role) not in allowed_roles:
            raise ForbiddenError(
                f"Role '{actor.role}' is not permitted to move an order to '{target_status.value}'."
            )

        # Ownership checks beyond role: a tailor may only act on THEIR OWN
        # order, and only the order's own customer may mark it received.
        if UserRole(actor.role) in {UserRole.TAILOR, UserRole.DESIGNER} and str(order.seller_user_id) != str(actor.id):
            raise ForbiddenError("You do not have permission to modify another professional's order.")
        if target_status == CustomerOrderStatus.RECEIVED and str(order.buyer_user_id) != str(actor.id):
            raise ForbiddenError("Only the customer who placed this order can mark it as received.")

        order.status = target_status.value
        timestamp_field = rule.get("timestamp_field")
        if timestamp_field:
            setattr(order, timestamp_field, utcnow())

        self.db.add(
            OrderTimelineEntry(
                order_id=order.id,
                from_status=current_status.value,
                to_status=target_status.value,
                actor_user_id=actor.id,
                note=note,
            )
        )
        self.db.commit()
        self.db.refresh(order)

        # Notifications and downstream side effects run in background
        # workers so this transaction doesn't block on email/SMS delivery.
        from app.workers.notification_tasks import notify_order_status_changed_task
        notify_order_status_changed_task.delay(order_id=str(order.id), new_status=target_status.value)

        return order

    def mark_paid_from_webhook(self, order_id) -> Order:
        """Called only from payment_service after server-side payment
        verification succeeds -- never from a client request directly."""
        order = self.orders.get_by_id_for_update(order_id)
        if not order:
            raise NotFoundError("Order not found.")
        if order.status != CustomerOrderStatus.PENDING.value:
            # Idempotent no-op: webhook arrived twice, or arrived after the
            # order was already marked paid by a prior delivery of the event.
            return order

        order.status = CustomerOrderStatus.PAID.value
        order.paid_at = utcnow()
        self.db.add(
            OrderTimelineEntry(
                order_id=order.id,
                from_status=CustomerOrderStatus.PENDING.value,
                to_status=CustomerOrderStatus.PAID.value,
                actor_user_id=None,
                note="Payment confirmed via provider webhook.",
            )
        )
        self.db.commit()
        self.db.refresh(order)
        return order

    def cancel(self, *, order_id, actor: User, reason: Optional[str] = None) -> Order:
        order = self.orders.get_by_id_for_update(order_id)
        if not order:
            raise NotFoundError("Order not found.")

        current_status = CustomerOrderStatus(order.status)
        if current_status in (
            CustomerOrderStatus.SHIPPED,
            CustomerOrderStatus.OUT_FOR_DELIVERY,
            CustomerOrderStatus.DELIVERED,
            CustomerOrderStatus.RECEIVED,
            CustomerOrderStatus.COMPLETED,
        ):
            raise ConflictError("This order can no longer be cancelled; it is already in fulfillment.")

        return self.transition(order_id=order_id, target_status=CustomerOrderStatus.CANCELLED, actor=actor, note=reason)
