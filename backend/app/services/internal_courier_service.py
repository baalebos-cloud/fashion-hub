"""Minimal internal courier dispatch and fulfillment with database authorization.

This is an explicit polling workflow for verified couriers, NOT a
geo-matching or third-party shipping integration.
"""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, InvalidStateTransitionError, NotFoundError
from app.core.timezone import utcnow
from app.models.address import Address
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.notification import Notification
from app.models.order import Order
from app.models.order_timeline import OrderTimelineEntry
from app.models.professional import Professional
from app.repositories.order_repository import OrderRepository

REQUESTABLE = {"ready_for_delivery", "shipped"}
STATUS_ACTIONS = {
    "picked-up": ("shipped", "assigned", "out_for_delivery", "in_transit", "out_for_delivery_at"),
    "delivered": ("out_for_delivery", "in_transit", "delivered", "delivered", "delivered_at"),
}


class InternalCourierService:
    def __init__(self, db: Session):
        self.db = db

    def request(self, *, order_id, actor):
        order = OrderRepository(self.db).get_by_id_for_update(order_id)
        if not order:
            raise NotFoundError("Order not found.")
        if order.order_type != "customer_order":
            raise ConflictError("Internal courier dispatch currently supports customer orders only.")
        if str(order.seller_user_id) != str(actor.id) or actor.role not in {"tailor", "designer"}:
            raise ForbiddenError("Only this order's professional may request delivery.")
        if order.status not in REQUESTABLE:
            raise ConflictError("The order must be ready for delivery.")
        existing = (self.db.query(DeliveryRequest).filter_by(order_id=order.id)
                    .order_by(DeliveryRequest.created_at.desc()).first())
        if existing:
            return existing

        profile = self.db.query(Professional).filter_by(user_id=actor.id).first()
        address = self.db.get(Address, order.delivery_address_id) if order.delivery_address_id else None
        if not profile or not profile.location_id:
            raise ConflictError("Set your business pickup location before dispatch.")
        if not address or address.user_id != order.buyer_user_id:
            raise ConflictError("The customer's delivery address is unavailable.")

        request = DeliveryRequest(
            order_id=order.id,
            pickup_location_id=profile.location_id,
            dropoff_location_id=address.location_id,
            package_description="Customer fashion order " + order.order_number,
            proposed_fee=order.delivery_fee,
            status="requested",
        )
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def list_available(self, *, actor, limit=20):
        self._verified_available_partner(actor)
        return (self.db.query(DeliveryRequest).join(Order, Order.id == DeliveryRequest.order_id)
                .filter(DeliveryRequest.status == "requested",
                        Order.order_type == "customer_order", Order.status.in_(REQUESTABLE))
                .order_by(DeliveryRequest.created_at, DeliveryRequest.id).limit(limit).all())

    def _verified_available_partner(self, actor):
        if actor.role != "delivery_partner":
            raise ForbiddenError("Only delivery partners may accept deliveries.")
        partner = (self.db.query(DeliveryPartner).filter_by(user_id=actor.id)
                   .with_for_update().populate_existing().first())
        if not partner or not partner.is_verified or not partner.is_available:
            raise ForbiddenError("A verified and available courier profile is required.")
        return partner

    def accept(self, *, request_id, actor):
        # Lock the available courier before claiming an order. A courier cannot
        # accept two assignments concurrently from separate requests.
        partner = self._verified_available_partner(actor)
        request = (self.db.query(DeliveryRequest).filter_by(id=request_id)
                   .with_for_update().populate_existing().first())
        if not request or request.status != "requested":
            raise NotFoundError("Available delivery request not found.")
        order = self.db.get(Order, request.order_id)
        if not order or order.order_type != "customer_order" or order.status not in REQUESTABLE:
            raise ConflictError("This order is no longer ready for dispatch.")
        if self.db.query(Delivery).filter_by(order_id=order.id).first():
            raise ConflictError("This order already has an assigned delivery.")
        request.status = "assigned"
        partner.is_available = False
        delivery = Delivery(
            delivery_request_id=request.id, order_id=order.id,
            delivery_partner_id=partner.id, status="assigned", provider="internal",
            delivery_fee=order.delivery_fee,
        )
        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)
        return delivery

    def get(self, *, delivery_id, actor):
        delivery = self.db.get(Delivery, delivery_id)
        if not delivery:
            raise NotFoundError("Delivery not found.")
        order = self.db.get(Order, delivery.order_id)
        partner = self.db.get(DeliveryPartner, delivery.delivery_partner_id) if delivery.delivery_partner_id else None
        permitted = (
            actor.role == "admin"
            or (order and str(actor.id) in {str(order.buyer_user_id), str(order.seller_user_id)})
            or (partner and str(partner.user_id) == str(actor.id))
        )
        if not permitted:
            raise NotFoundError("Delivery not found.")
        return delivery

    def transition(self, *, delivery_id, actor, action):
        if action not in STATUS_ACTIONS:
            raise ConflictError("Unknown courier action.")
        # Lock the order first for consistency with order lifecycle operations.
        initial = self.db.get(Delivery, delivery_id)
        if not initial:
            raise NotFoundError("Delivery not found.")
        order = OrderRepository(self.db).get_by_id_for_update(initial.order_id)
        delivery = (self.db.query(Delivery).filter_by(id=delivery_id)
                    .with_for_update().populate_existing().first())
        partner = self.db.get(DeliveryPartner, delivery.delivery_partner_id) if delivery else None
        if not order or not delivery or not partner or actor.role != "delivery_partner" or str(partner.user_id) != str(actor.id):
            raise NotFoundError("Assigned delivery not found.")
        if order.order_type != "customer_order":
            raise ConflictError("Unsupported delivery type.")
        expected_order, expected_delivery, new_order, new_delivery, stamp_field = STATUS_ACTIONS[action]
        if order.status != expected_order or delivery.status != expected_delivery:
            raise InvalidStateTransitionError("The delivery is not in the required state.")
        now = utcnow()
        previous_status = order.status
        order.status = new_order
        setattr(order, stamp_field, now)
        delivery.status = new_delivery
        if action == "picked-up":
            delivery.picked_up_at = now
        else:
            delivery.delivered_at = now
            partner.is_available = True
        self.db.add(OrderTimelineEntry(
            order_id=order.id, from_status=previous_status, to_status=new_order,
            actor_user_id=actor.id, note="Courier " + action,
        ))
        for recipient in {order.buyer_user_id, order.seller_user_id}:
            self.db.add(Notification(
                recipient_user_id=recipient, channel="in_app",
                event_type="order." + new_order,
                title="Order delivery updated",
                body="Order " + order.order_number + " is now " + new_order.replace("_", " ") + ".",
            ))
        self.db.commit()
        self.db.refresh(delivery)
        return delivery
