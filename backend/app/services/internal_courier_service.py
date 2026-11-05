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
from app.models.location import Location
from app.models.user import User
from app.services.dispatch_routing import estimate_straight_line_km, validate_point
from app.services.delivery_handover import handover_code, verify_handover_code
from app.services.delivery_position import clear_position, read_position, save_position, start_sharing
from app.models.order import Order
from app.models.order_timeline import OrderTimelineEntry
from app.models.professional import Professional
from app.repositories.order_repository import OrderRepository

REQUESTABLE = {"ready_for_delivery", "shipped"}
STATUS_ACTIONS = {
    "picked-up": (("ready_for_delivery", "shipped"), "assigned", "out_for_delivery", "in_transit", "out_for_delivery_at"),
    "delivered": (("out_for_delivery",), "in_transit", "delivered", "delivered", "delivered_at"),
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
        if address and address.user_id != order.buyer_user_id:
            raise ConflictError("The customer's delivery address is unavailable.")
        snapshot = order.delivery_address_snapshot or {}
        if not isinstance(snapshot, dict):
            snapshot = {}
        pickup_source = self.db.get(Location, profile.location_id)
        if address is not None:
            dropoff_source = self.db.get(Location, address.location_id)
        elif snapshot.get("formatted_address") and snapshot.get("latitude") is not None and snapshot.get("longitude") is not None:
            # A customer can delete their saved address after ordering. The
            # order's checkout snapshot still belongs to this order and is
            # authoritative for fulfillment.
            dropoff_source = Location(
                location_type="delivery_dropoff",
                latitude=snapshot["latitude"], longitude=snapshot["longitude"],
                formatted_address=snapshot["formatted_address"],
                city=snapshot.get("city"), state_region=snapshot.get("state_region"),
                country=snapshot.get("country"), postal_code=snapshot.get("postal_code"),
            )
        else:
            dropoff_source = None
        if pickup_source is None or dropoff_source is None:
            raise ConflictError("Pickup and drop-off location details are required.")
        # An accepted delivery must not silently change destination when a
        # customer edits a saved address or the tailor moves their workshop.
        def snapshot_location(source, location_type, fields=None):
            fields = fields or {}
            return Location(
                location_type=location_type,
                latitude=fields.get("latitude", source.latitude),
                longitude=fields.get("longitude", source.longitude),
                formatted_address=fields.get("formatted_address", source.formatted_address),
                city=fields.get("city", source.city),
                state_region=fields.get("state_region", source.state_region),
                country=fields.get("country", source.country),
                postal_code=fields.get("postal_code", source.postal_code),
            )
        pickup_snapshot = snapshot_location(pickup_source, "delivery_pickup")
        dropoff_snapshot = snapshot_location(
            dropoff_source, "delivery_dropoff", order.delivery_address_snapshot,
        )
        self.db.add(pickup_snapshot)
        self.db.add(dropoff_snapshot)
        self.db.flush()
        request = DeliveryRequest(
            order_id=order.id,
            pickup_location_id=pickup_snapshot.id,
            dropoff_location_id=dropoff_snapshot.id,
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

    def trip(self, *, delivery_id, actor):
        """Fulfillment contacts and exact pins are available only to parties on this order."""
        delivery = self.get(delivery_id=delivery_id, actor=actor)
        request = self.db.get(DeliveryRequest, delivery.delivery_request_id)
        if request is None:
            raise NotFoundError("Delivery request not found.")
        order = self.db.get(Order, delivery.order_id)
        pickup = self.db.get(Location, request.pickup_location_id)
        dropoff = self.db.get(Location, request.dropoff_location_id)
        if not order or not pickup or not dropoff:
            raise NotFoundError("Delivery route is unavailable.")
        address = self.db.get(Address, order.delivery_address_id) if order.delivery_address_id else None
        seller = self.db.get(User, order.seller_user_id)
        origin = validate_point(pickup.latitude, pickup.longitude)
        destination = validate_point(dropoff.latitude, dropoff.longitude)
        return {
            "id": delivery.id, "order_id": order.id, "status": delivery.status,
            "delivery_fee": float(delivery.delivery_fee),
            "pickup": {
                "address": pickup.formatted_address,
                **(origin or {"latitude": None, "longitude": None}),
                "contact_name": seller.full_name if seller else None,
                "contact_phone": seller.phone_number if seller else None,
            },
            "dropoff": {
                "address": dropoff.formatted_address,
                **(destination or {"latitude": None, "longitude": None}),
                "contact_name": (order.delivery_address_snapshot or {}).get("recipient_name")
                    or (address.recipient_name if address else None),
                "contact_phone": (order.delivery_address_snapshot or {}).get("recipient_phone")
                    or (address.recipient_phone if address else None),
            },
            "straight_line_km": estimate_straight_line_km(origin, destination),
            "distance_source": "haversine",
        }

    def _assigned_rider_for_position(self, *, delivery_id, actor):
        delivery = self.get(delivery_id=delivery_id, actor=actor)
        partner = self.db.get(DeliveryPartner, delivery.delivery_partner_id) if delivery.delivery_partner_id else None
        if (actor.role != "delivery_partner" or not partner
                or str(partner.user_id) != str(actor.id)):
            raise NotFoundError("Assigned delivery not found.")
        return delivery

    def begin_position(self, *, delivery_id, actor):
        delivery = self._assigned_rider_for_position(delivery_id=delivery_id, actor=actor)
        if delivery.status != "in_transit":
            raise ConflictError("GPS sharing is available only after pickup and before handover.")
        return start_sharing(delivery.id)

    def report_position(self, *, delivery_id, actor, latitude, longitude, accuracy_m, share_token):
        delivery = self._assigned_rider_for_position(delivery_id=delivery_id, actor=actor)
        if delivery.status != "in_transit":
            raise ConflictError("Live GPS is available only after pickup and before handover.")
        return save_position(
            delivery.id, share_token=share_token, latitude=latitude,
            longitude=longitude, accuracy_m=accuracy_m,
        )

    def stop_position(self, *, delivery_id, actor):
        delivery = self._assigned_rider_for_position(delivery_id=delivery_id, actor=actor)
        clear_position(delivery.id)

    def current_position(self, *, delivery_id, actor):
        delivery = self.get(delivery_id=delivery_id, actor=actor)
        if delivery.status != "in_transit":
            return None
        return read_position(delivery.id)

    def customer_handover_code(self, *, delivery_id, actor):
        """The buyer alone sees the code after the courier has collected the order."""
        delivery = self.get(delivery_id=delivery_id, actor=actor)
        order = self.db.get(Order, delivery.order_id)
        if not order or str(order.buyer_user_id) != str(actor.id):
            raise NotFoundError("Delivery not found.")
        if delivery.status != "in_transit" or order.status != "out_for_delivery":
            raise ConflictError("The package must be picked up before issuing a handover code.")
        return {"delivery_id": delivery.id, "handover_code": handover_code(delivery.id)}

    def transition(self, *, delivery_id, actor, action, handover_code_input=None):
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
        if order.status not in expected_order or delivery.status != expected_delivery:
            raise InvalidStateTransitionError("The delivery is not in the required state.")
        if action == "delivered":
            verify_handover_code(delivery.id, handover_code_input)
        now = utcnow()
        previous_status = order.status
        order.status = new_order
        setattr(order, stamp_field, now)
        delivery.status = new_delivery
        if action == "picked-up":
            order.shipped_at = order.shipped_at or now
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
