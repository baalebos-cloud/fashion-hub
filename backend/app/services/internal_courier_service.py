"""Minimal internal courier dispatch and fulfillment with database authorization.

This is an explicit polling workflow for verified couriers, NOT a
geo-matching or third-party shipping integration.
"""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, InvalidStateTransitionError, NotFoundError
from app.core.timezone import utcnow
from app.core.logging import get_logger
from app.models.address import Address
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.notification import Notification
from app.models.location import LOCAL_ADDRESS_FIELDS, Location
from app.models.user import User
from app.services.dispatch_routing import estimate_straight_line_km, validate_point
from app.core.config import settings
from app.core.exceptions import ValidationAppError
from app.models.delivery_proof import DeliveryEvent
from app.services.delivery_handover import DeliveryCodeService, record_event, validate_idempotency_key
from app.services.delivery_position import clear_position, read_position, save_position, start_sharing
from app.models.order import Order
from app.models.order_timeline import OrderTimelineEntry
from app.models.professional import Professional
from app.repositories.order_repository import OrderRepository

# Each order is its own delivery leg: a customer garment (tailor -> customer) or
# a materials order (vendor -> tailor). Statuses below are per order type.
logger = get_logger(__name__)

REQUESTABLE_BY_TYPE = {
    "customer_order": {"ready_for_delivery", "shipped"},
    "vendor_order": {"ready_for_pickup"},
}
# Union kept for callers that only need "is this order waiting for a rider".
REQUESTABLE = set().union(*REQUESTABLE_BY_TYPE.values())
# (order_type, action) -> (expected order states, expected delivery state,
#                          new order state, new delivery state, order timestamp field)
STATUS_ACTIONS = {
    ("customer_order", "picked-up"): (("ready_for_delivery", "shipped"), "assigned", "out_for_delivery", "in_transit", "out_for_delivery_at"),
    ("customer_order", "delivered"): (("out_for_delivery",), "in_transit", "delivered", "delivered", "delivered_at"),
    ("vendor_order", "picked-up"): (("ready_for_pickup",), "assigned", "in_transit", "in_transit", "out_for_delivery_at"),
    ("vendor_order", "delivered"): (("in_transit",), "in_transit", "delivered", "delivered", "delivered_at"),
}
# Status in which the buyer may reveal the handover code (package collected, not yet handed over).
HANDOVER_STATUS = {"customer_order": "out_for_delivery", "vendor_order": "in_transit"}


def _local_details(location) -> dict:
    """LGA, landmark, bus stop and instructions for the assigned rider's route view."""
    return {f: getattr(location, f, None) for f in LOCAL_ADDRESS_FIELDS}


def is_dispatchable(order) -> bool:
    return order is not None and order.status in REQUESTABLE_BY_TYPE.get(order.order_type, set())


class InternalCourierService:
    def __init__(self, db: Session):
        self.db = db

    def request(self, *, order_id, actor):
        order = OrderRepository(self.db).get_by_id_for_update(order_id)
        if not order:
            raise NotFoundError("Order not found.")
        seller_roles = {"customer_order": {"tailor", "designer"}, "vendor_order": {"vendor"}}
        if order.order_type not in seller_roles:
            raise ConflictError("This order type can't be dispatched.")
        if str(order.seller_user_id) != str(actor.id) or actor.role not in seller_roles[order.order_type]:
            raise ForbiddenError("Only this order's seller may request delivery.")
        if not is_dispatchable(order):
            raise ConflictError("The order must be ready for pickup before requesting a rider.")
        # Re-requesting is idempotent while a search or run is live; a cancelled
        # request (admin stopped the search or released a rider) allows a new one.
        existing = (self.db.query(DeliveryRequest)
                    .filter(DeliveryRequest.order_id == order.id,
                            DeliveryRequest.status.in_(("requested", "assigned")))
                    .order_by(DeliveryRequest.created_at.desc()).first())
        if existing:
            return existing

        if order.order_type == "vendor_order":
            from app.models.vendor import Vendor
            vendor = self.db.query(Vendor).filter_by(user_id=actor.id).first()
            pickup_location_id = vendor.warehouse_location_id if vendor else None
            if not pickup_location_id:
                raise ConflictError("Set your store pickup location before requesting a rider.")
        else:
            profile = self.db.query(Professional).filter_by(user_id=actor.id).first()
            pickup_location_id = profile.location_id if profile else None
            if not pickup_location_id:
                raise ConflictError("Set your business pickup location before dispatch.")
        address = self.db.get(Address, order.delivery_address_id) if order.delivery_address_id else None
        if address and address.user_id != order.buyer_user_id:
            raise ConflictError("The customer's delivery address is unavailable.")
        snapshot = order.delivery_address_snapshot or {}
        if not isinstance(snapshot, dict):
            snapshot = {}
        pickup_source = self.db.get(Location, pickup_location_id)
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
                **{f: snapshot.get(f) for f in LOCAL_ADDRESS_FIELDS},
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
                **{f: fields.get(f, getattr(source, f)) for f in LOCAL_ADDRESS_FIELDS},
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
            package_description=("Materials order " if order.order_type == "vendor_order"
                                 else "Customer fashion order ") + order.order_number,
            proposed_fee=self._suggested_fee(order, pickup_snapshot, dropoff_snapshot),
            status="requested",
        )
        self._attach_route(request, order, pickup_snapshot, dropoff_snapshot)
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        self._start_auto_offers(request.id)
        return request

    @staticmethod
    def _attach_route(request, order, pickup, dropoff) -> None:
        """Compute the pickup -> drop-off road route once and keep it on the request. Never
        blocks the request: a routing failure stores the labelled straight-line estimate."""
        from app.services import route_service
        try:
            estimate = route_service.route(validate_point(pickup.latitude, pickup.longitude),
                                           validate_point(dropoff.latitude, dropoff.longitude), "bike")
        except Exception as exc:  # noqa: BLE001 - bad pins: no route, the request still goes out
            logger.warning("route_attach_failed", extra={"error_type": type(exc).__name__})
            return
        if estimate is None:
            return
        request.route_distance_km = estimate.distance_km
        request.route_duration_minutes = estimate.duration_minutes
        request.route_source = estimate.source
        request.route_polyline = estimate.polyline
        request.route_computed_at = utcnow()
        if (settings.DISPATCH_PRICE_FROM_ROAD_ROUTES and estimate.verified
                and not (order.delivery_fee and float(order.delivery_fee) > 0)):
            from app.services.dispatch_pricing import suggested_fare_for_road_km
            request.proposed_fee = suggested_fare_for_road_km(estimate.distance_km)

    def _start_auto_offers(self, request_id) -> None:
        from app.services.auto_dispatch_service import AutoDispatchService, auto_offers_enabled
        if not auto_offers_enabled():
            return
        try:
            AutoDispatchService(self.db).offer_next(request_id)
        except Exception as exc:  # noqa: BLE001 - the open job board still works if offering fails.
            self.db.rollback()
            logger.warning("auto_dispatch_start_failed", extra={"error_type": type(exc).__name__})

    @staticmethod
    def _suggested_fee(order, pickup, dropoff):
        """Keep a fee already priced into the order; otherwise suggest one from distance."""
        from app.services.dispatch_pricing import suggested_fare
        if order.delivery_fee and float(order.delivery_fee) > 0:
            return order.delivery_fee
        try:
            km = estimate_straight_line_km(validate_point(pickup.latitude, pickup.longitude),
                                           validate_point(dropoff.latitude, dropoff.longitude))
        except Exception:  # noqa: BLE001 - bad pins fall back to the minimum fare.
            km = None
        return suggested_fare(km)

    def list_available(self, *, actor, limit=20):
        partner = self._verified_available_partner(actor)
        from app.services.auto_dispatch_service import AutoDispatchService, auto_offers_enabled
        held = set()
        if auto_offers_enabled():
            auto = AutoDispatchService(self.db)
            auto.advance_expired()
            held = auto.held_request_ids(exclude_partner_id=partner.id)
        return (self.db.query(DeliveryRequest).join(Order, Order.id == DeliveryRequest.order_id)
                .filter(DeliveryRequest.id.notin_(held) if held else True)
                .filter(DeliveryRequest.status == "requested",
                        or_(*[(Order.order_type == kind) & Order.status.in_(states)
                              for kind, states in REQUESTABLE_BY_TYPE.items()]))
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
        if not is_dispatchable(order):
            raise ConflictError("This order is no longer ready for dispatch.")
        from app.services.auto_dispatch_service import AutoDispatchService, auto_offers_enabled
        if auto_offers_enabled() and AutoDispatchService(self.db).held_by_other(request.id, partner.id):
            raise ConflictError("This job is reserved for another rider right now. Try again shortly.")
        return self.assign(request=request, order=order, partner=partner, fee=request.proposed_fee)

    def assign(self, *, request, order, partner, fee, accepted_offer_id=None):
        """Assign a locked request to a locked, available partner. Shared by instant
        claims and accepted fare offers; caller must hold both row locks."""
        from app.models.delivery_offer import DeliveryOffer
        if self.db.query(Delivery.id).filter(Delivery.order_id == order.id,
                                             Delivery.status != "cancelled").first():
            raise ConflictError("This order already has an assigned delivery.")
        request.status = "assigned"
        partner.is_available = False
        delivery = Delivery(
            delivery_request_id=request.id, order_id=order.id,
            delivery_partner_id=partner.id, status="assigned", provider="internal",
            delivery_fee=fee if fee is not None else order.delivery_fee,
        )
        self.db.add(delivery)
        from app.models.dispatch_job_offer import DispatchJobOffer
        self.db.query(DispatchJobOffer).filter(
            DispatchJobOffer.delivery_request_id == request.id, DispatchJobOffer.status == "offered",
        ).update({DispatchJobOffer.status: "withdrawn", DispatchJobOffer.responded_at: utcnow()},
                 synchronize_session=False)
        # The rider is now busy: jobs still reserved for them elsewhere go to the next rider.
        stranded = [row[0] for row in self.db.query(DispatchJobOffer.delivery_request_id).filter(
            DispatchJobOffer.delivery_partner_id == partner.id, DispatchJobOffer.status == "offered").all()]
        if stranded:
            self.db.query(DispatchJobOffer).filter(
                DispatchJobOffer.delivery_partner_id == partner.id, DispatchJobOffer.status == "offered",
            ).update({DispatchJobOffer.status: "withdrawn", DispatchJobOffer.responded_at: utcnow()},
                     synchronize_session=False)
        for offer in self.db.query(DeliveryOffer).filter(
                DeliveryOffer.delivery_request_id == request.id, DeliveryOffer.status == "pending"):
            offer.status = "accepted" if accepted_offer_id and offer.id == accepted_offer_id else "declined"
        self.db.commit()
        self.db.refresh(delivery)
        for request_id in stranded:
            self._start_auto_offers(request_id)
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
        # A rider released by dispatch immediately loses access to the route and contacts.
        if (delivery.status == "cancelled" and actor.role == "delivery_partner"
                and partner is not None and str(partner.user_id) == str(actor.id)):
            raise NotFoundError("Delivery not found.")
        return delivery

    def trip(self, *, delivery_id, actor):
        """Fulfillment contacts and exact pins are available only to parties on this order."""
        from app.services import route_service
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
                **_local_details(pickup),
                "contact_name": seller.full_name if seller else None,
                "can_call": bool(seller and seller.phone_number),
            },
            "dropoff": {
                "address": dropoff.formatted_address,
                **_local_details(dropoff),
                **(destination or {"latitude": None, "longitude": None}),
                "contact_name": (order.delivery_address_snapshot or {}).get("recipient_name")
                    or (address.recipient_name if address else None),
                "can_call": bool((order.delivery_address_snapshot or {}).get("recipient_phone")
                                 or (address.recipient_phone if address else None)),
            },
            "straight_line_km": estimate_straight_line_km(origin, destination),
            "route": ({**route_service.stored_route(request), "polyline": request.route_polyline}
                      if route_service.stored_route(request) else None),
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

    def report_position(self, *, delivery_id, actor, latitude, longitude, accuracy_m, share_token,
                        recorded_at=None, speed_mps=None):
        delivery = self._assigned_rider_for_position(delivery_id=delivery_id, actor=actor)
        if delivery.status != "in_transit":
            raise ConflictError("Live GPS is available only after pickup and before handover.")
        point = save_position(
            delivery.id, share_token=share_token, latitude=latitude,
            longitude=longitude, accuracy_m=accuracy_m, recorded_at=recorded_at, speed_mps=speed_mps,
        )
        if point.get("accepted"):
            from app.services.delivery_proximity import check_proximity
            check_proximity(self.db, delivery, latitude=latitude, longitude=longitude, accuracy_m=accuracy_m)
        return point

    def report_device_state(self, *, delivery_id, actor, share_token, state):
        delivery = self._assigned_rider_for_position(delivery_id=delivery_id, actor=actor)
        from app.services.delivery_position import report_device_state
        report_device_state(delivery.id, share_token=share_token, state=state)

    def stop_position(self, *, delivery_id, actor):
        delivery = self._assigned_rider_for_position(delivery_id=delivery_id, actor=actor)
        clear_position(delivery.id)

    def current_position(self, *, delivery_id, actor):
        delivery = self.get(delivery_id=delivery_id, actor=actor)
        if delivery.status != "in_transit":
            return None
        return read_position(delivery.id)

    def _lock_for_code(self, delivery_id):
        """Order -> delivery lock order, same as transition(), so codes and status never race."""
        initial = self.db.get(Delivery, delivery_id)
        order = OrderRepository(self.db).get_by_id_for_update(initial.order_id)
        delivery = (self.db.query(Delivery).filter_by(id=delivery_id)
                    .with_for_update().populate_existing().first())
        return order, delivery

    def customer_handover_code(self, *, delivery_id, actor, rotate: bool = False):
        """The buyer alone sees the code after the courier has collected the order. Codes expire
        and rotate; the rider never receives one."""
        delivery = self.get(delivery_id=delivery_id, actor=actor)
        order = self.db.get(Order, delivery.order_id)
        if not order or str(order.buyer_user_id) != str(actor.id):
            raise NotFoundError("Delivery not found.")
        order, delivery = self._lock_for_code(delivery.id)
        if delivery.status != "in_transit" or order.status != HANDOVER_STATUS.get(order.order_type):
            raise ConflictError("The package must be picked up before issuing a handover code.")
        issued = DeliveryCodeService(self.db).reveal(delivery=delivery, purpose="handover", actor=actor, rotate=rotate)
        self.db.commit()
        return {"delivery_id": delivery.id, "handover_code": issued["code"], "expires_at": issued["expires_at"],
                "package_count": delivery.package_count}

    def seller_pickup_code(self, *, delivery_id, actor, rotate: bool = False):
        """The seller alone sees the pickup code while a rider is on the way to collect."""
        delivery = self.get(delivery_id=delivery_id, actor=actor)
        order = self.db.get(Order, delivery.order_id)
        if not order or str(order.seller_user_id) != str(actor.id):
            raise NotFoundError("Delivery not found.")
        if not settings.DELIVERY_PICKUP_CODE_REQUIRED:
            return {"delivery_id": delivery.id, "required": False, "pickup_code": None, "expires_at": None}
        order, delivery = self._lock_for_code(delivery.id)
        expected_order = STATUS_ACTIONS.get((order.order_type, "picked-up"), ((),))[0]
        if delivery.status != "assigned" or order.status not in expected_order:
            raise ConflictError("A pickup code is available only while a rider is coming to collect.")
        issued = DeliveryCodeService(self.db).reveal(delivery=delivery, purpose="pickup", actor=actor, rotate=rotate)
        self.db.commit()
        return {"delivery_id": delivery.id, "required": True, "pickup_code": issued["code"],
                "expires_at": issued["expires_at"]}

    def events(self, *, delivery_id, actor):
        """Admin view of a run's audit trail."""
        if actor.role != "admin":
            raise NotFoundError("Delivery not found.")
        if not self.db.get(Delivery, delivery_id):
            raise NotFoundError("Delivery not found.")
        return (self.db.query(DeliveryEvent).filter(DeliveryEvent.delivery_id == delivery_id)
                .order_by(DeliveryEvent.seq).all())

    def transition(self, *, delivery_id, actor, action, handover_code_input=None, pickup_code_input=None,
                   package_count: int | None = None, idempotency_key: str | None = None):
        if action not in {"picked-up", "delivered"}:
            raise ConflictError("Unknown courier action.")
        key = validate_idempotency_key(idempotency_key)
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
        event_type = "picked_up" if action == "picked-up" else "delivered"
        if key:
            prior = (self.db.query(DeliveryEvent)
                     .filter(DeliveryEvent.delivery_id == delivery.id, DeliveryEvent.idempotency_key == key).first())
            if prior is not None:
                # A retried request (flaky network): answer with the current state, change nothing.
                if prior.event_type != event_type or str(prior.actor_user_id) != str(actor.id):
                    raise ConflictError("This Idempotency-Key was already used for a different action.")
                self.db.commit()
                return delivery
        if (order.order_type, action) not in STATUS_ACTIONS:
            raise ConflictError("Unsupported delivery type.")
        expected_order, expected_delivery, new_order, new_delivery, stamp_field = STATUS_ACTIONS[(order.order_type, action)]
        if order.status not in expected_order or delivery.status != expected_delivery:
            raise InvalidStateTransitionError("The delivery is not in the required state.")
        if action == "picked-up" and package_count is not None and not 1 <= package_count <= 50:
            raise ValidationAppError("Package count must be between 1 and 50.")
        purpose = "handover" if action == "delivered" else ("pickup" if settings.DELIVERY_PICKUP_CODE_REQUIRED else None)
        if purpose:
            try:
                DeliveryCodeService(self.db).verify(
                    delivery=delivery, purpose=purpose,
                    submitted=handover_code_input if purpose == "handover" else pickup_code_input)
            except (ValidationAppError, ForbiddenError) as exc:
                # Keep a record of failed attempts even though the transition itself rolls back.
                self.db.rollback()
                failed = self.db.get(Delivery, delivery_id)
                record_event(self.db, delivery=failed, event_type=f"{purpose}_verification_failed", actor=actor,
                             reason="locked" if isinstance(exc, ForbiddenError) else "rejected")
                self.db.commit()
                raise
        now = utcnow()
        previous_status = order.status
        order.status = new_order
        setattr(order, stamp_field, now)
        delivery.status = new_delivery
        if action == "picked-up":
            order.shipped_at = order.shipped_at or now
            delivery.picked_up_at = now
            delivery.package_count = package_count or 1
        else:
            delivery.delivered_at = now
            partner.is_available = True
            try:
                clear_position(delivery.id)  # tracking ends at handover
            except Exception:  # noqa: BLE001 - the point expires on its own; never block delivery
                logger.warning("gps_clear_on_delivery_failed")
        record_event(self.db, delivery=delivery, event_type=event_type, actor=actor, idempotency_key=key,
                     package_count=delivery.package_count,
                     verified_by=f"{purpose}_code" if purpose else "rider_confirmation")
        if order.order_type == "vendor_order" and action == "picked-up":
            # Materials orders record the collection itself before going in transit.
            self.db.add(OrderTimelineEntry(order_id=order.id, from_status=previous_status, to_status="picked_up",
                                           actor_user_id=actor.id, note="Courier collected the materials"))
            previous_status = "picked_up"
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
