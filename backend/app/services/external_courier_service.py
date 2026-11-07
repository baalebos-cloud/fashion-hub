"""Send a delivery with an external courier company (logistics phase 6).

Flow (dispatcher-driven, audited):
  quotes(request)          ask each enabled courier that can take the job
  book(request, courier)   lock order -> request; book with the courier (idempotency key = request
                           id); record a Delivery(provider=<courier>, provider_tracking_reference=
                           <their id>), no rider. If our save fails after the courier booked, we
                           cancel with the courier so nothing is left orphaned.
  handle_event(...)        signed webhook or reconciliation poll -> normalised status. Each courier
                           event is stored once (duplicates ignored), progress only moves forward,
                           and order status follows the same STATUS_ACTIONS as our own riders.
  reconcile()              poll couriers for non-final deliveries, to catch missed webhooks.

Money: quotes are recorded on the delivery for reference. Nothing here charges, refunds or pays out.
Internal riders, codes and flows are untouched; an external delivery has no rider and uses the
courier's proof of delivery instead of our handover code.
"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.core.timezone import utcnow
from app.integrations.couriers import enabled_couriers, get_courier
from app.integrations.couriers.base import FINAL, CourierError, CourierEvent, CourierJob
from app.models.audit_log import AuditLog
from app.models.courier_event import CourierEventRecord
from app.models.delivery import Delivery
from app.models.delivery_request import DeliveryRequest
from app.models.location import Location
from app.models.notification import Notification
from app.models.order import Order
from app.models.order_timeline import OrderTimelineEntry
from app.repositories.order_repository import OrderRepository
from app.services.delivery_handover import record_event
from app.services.internal_courier_service import STATUS_ACTIONS, is_dispatchable

logger = get_logger(__name__)
# Our delivery states for each courier status (forward-only).
PROGRESS = {"assigned": 0, "in_transit": 1, "delivered": 2}
DELIVERY_STATE = {"booked": "assigned", "courier_assigned": "assigned", "picked_up": "in_transit",
                  "in_transit": "in_transit", "delivered": "delivered"}


def _waypoint(location: Location | None) -> dict:
    if location is None or location.latitude is None or location.longitude is None:
        raise ValidationAppError("Pickup and drop-off need map pins before booking a courier.")
    return {"latitude": float(location.latitude), "longitude": float(location.longitude),
            "address": location.formatted_address}


class ExternalCourierService:
    def __init__(self, db: Session):
        self.db = db

    def _job(self, request: DeliveryRequest) -> CourierJob:
        return CourierJob(reference=str(request.id),
                          pickup=_waypoint(self.db.get(Location, request.pickup_location_id)),
                          dropoff=_waypoint(self.db.get(Location, request.dropoff_location_id)),
                          package_description=request.package_description or "Fashion order")

    # ---- quotes and booking ----------------------------------------------------------------------
    def quotes(self, request_id) -> list[dict]:
        request = self.db.get(DeliveryRequest, request_id)
        if request is None:
            raise NotFoundError("Delivery request not found.")
        job = self._job(request)
        results = []
        for name, courier in enabled_couriers().items():
            ok, reason = courier.eligible(job)
            if not ok:
                results.append({"courier": name, "name": courier.display_name, "available": False, "reason": reason})
                continue
            try:
                q = courier.quote(job)
            except CourierError as exc:
                results.append({"courier": name, "name": courier.display_name, "available": False,
                                "reason": f"Quote failed: {exc}"})
                continue
            results.append({"courier": name, "name": courier.display_name, "available": True, "quote_id": q.quote_id,
                            "amount_ngn": q.amount_ngn, "eta_minutes": q.eta_minutes,
                            "expires_at": q.expires_at.isoformat() if q.expires_at else None})
        return results

    def book(self, *, request_id, courier_name: str, quote_id: str, admin, reason: str, ip: str | None = None) -> Delivery:
        reason = (reason or "").strip()
        if len(reason) < 5:
            raise ValidationAppError("Give a short reason (at least 5 characters); it's kept in the audit log.")
        courier = get_courier(courier_name)
        if courier is None:
            raise ConflictError("That courier isn't enabled.")
        initial = self.db.get(DeliveryRequest, request_id)
        if initial is None:
            raise NotFoundError("Delivery request not found.")
        order = OrderRepository(self.db).get_by_id_for_update(initial.order_id)
        request = self.db.query(DeliveryRequest).filter_by(id=request_id).with_for_update().populate_existing().one()
        if request.status != "requested" or not is_dispatchable(order):
            raise ConflictError("This job already has a rider or courier, or isn't ready.")
        if self.db.query(Delivery.id).filter(Delivery.order_id == order.id, Delivery.status != "cancelled").first():
            raise ConflictError("This order already has an active delivery.")
        job = self._job(request)
        try:
            # Re-quote: book only at the price the dispatcher saw.
            fresh = courier.quote(job)
            if fresh.quote_id != quote_id:
                raise ConflictError("The courier's price has changed. Refresh the quotes and try again.")
            booking = courier.book(job, quote_id, idempotency_key=f"tailora-{request.id}")
        except CourierError as exc:
            self.db.rollback()
            raise ConflictError(f"{courier.display_name} couldn't take the booking: {exc}") from exc
        except ConflictError:
            self.db.rollback()
            raise
        amount = fresh.amount_ngn
        try:
            request.status = "assigned"
            delivery = Delivery(order_id=order.id, delivery_request_id=request.id, status="assigned",
                                provider=courier_name, provider_tracking_reference=booking.external_id,
                                delivery_fee=amount if amount is not None else (request.proposed_fee or 0))
            self.db.add(delivery)
            self.db.flush()
            record_event(self.db, delivery=delivery, event_type="courier_booked", actor=admin,
                         courier=courier_name, external_id=booking.external_id, tracking_url=booking.tracking_url)
            self.db.add(AuditLog(actor_user_id=admin.id, action="dispatch.courier_booked", resource_type="dispatch",
                                 resource_id=delivery.id, ip_address=ip,
                                 metadata_json={"reason": reason[:500], "courier": courier_name,
                                                "external_id": booking.external_id, "order_id": str(order.id)}))
            for user_id in {order.seller_user_id, order.buyer_user_id}:
                self.db.add(Notification(recipient_user_id=user_id, channel="in_app", event_type="dispatch.courier_booked",
                                         title="Courier booked",
                                         body=f"{courier.display_name} will deliver order {order.order_number}."))
            self.db.commit()
        except Exception:
            self.db.rollback()
            # Don't leave a paid-for courier booking with no record on our side.
            try:
                courier.cancel(booking.external_id)
            except CourierError:
                logger.error("courier_compensating_cancel_failed", extra={"courier": courier_name})
            raise
        return delivery

    def cancel(self, *, delivery_id, admin, reason: str, ip: str | None = None) -> Delivery:
        delivery = self.db.get(Delivery, delivery_id)
        if delivery is None or delivery.provider in (None, "internal"):
            raise NotFoundError("Courier delivery not found.")
        courier = get_courier(delivery.provider)
        if courier is None:
            raise ConflictError("That courier isn't enabled.")
        order = OrderRepository(self.db).get_by_id_for_update(delivery.order_id)
        delivery = self.db.query(Delivery).filter_by(id=delivery_id).with_for_update().populate_existing().one()
        if delivery.status != "assigned":
            raise ConflictError("The courier has already collected the package; resolve it with them directly.")
        try:
            courier.cancel(delivery.provider_tracking_reference)
        except CourierError as exc:
            self.db.rollback()
            raise ConflictError(f"The courier couldn't cancel: {exc}") from exc
        delivery.status = "cancelled"
        request = self.db.get(DeliveryRequest, delivery.delivery_request_id)
        if request is not None:
            request.status = "requested"  # back to looking for a rider or another courier
        record_event(self.db, delivery=delivery, event_type="courier_cancelled", actor=admin, reason=(reason or "")[:200])
        self.db.add(AuditLog(actor_user_id=admin.id, action="dispatch.courier_cancelled", resource_type="dispatch",
                             resource_id=delivery.id, ip_address=ip,
                             metadata_json={"reason": (reason or "")[:500], "order_id": str(order.id)}))
        self.db.commit()
        return delivery

    # ---- status updates -------------------------------------------------------------------------
    def handle_event(self, courier_name: str, event: CourierEvent) -> str:
        """Apply one courier status update. Returns applied | duplicate | ignored | unmatched."""
        delivery = (self.db.query(Delivery)
                    .filter(Delivery.provider == courier_name, Delivery.provider_tracking_reference == event.external_id)
                    .first())
        record = CourierEventRecord(courier=courier_name, event_id=event.event_id[:128], external_id=event.external_id,
                                    delivery_id=delivery.id if delivery else None, status=event.status,
                                    applied="unmatched" if delivery is None else "ignored", occurred_at=event.occurred_at,
                                    details={k: v for k, v in {"courier_name": event.courier_name,
                                                               "proof_of_delivery_url": event.proof_of_delivery_url,
                                                               "note": event.note}.items() if v})
        self.db.add(record)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            return "duplicate"
        if delivery is None:
            self.db.commit()
            return "unmatched"
        order = OrderRepository(self.db).get_by_id_for_update(delivery.order_id)
        delivery = self.db.query(Delivery).filter_by(id=delivery.id).with_for_update().populate_existing().one()
        outcome = self._apply(order, delivery, event)
        record.applied = outcome
        self.db.commit()
        return outcome

    def _apply(self, order: Order, delivery: Delivery, event: CourierEvent) -> str:
        if delivery.status in {"delivered", "cancelled", "failed"}:
            return "ignored"  # already final: late or out-of-order event
        if event.status in {"failed", "cancelled"}:
            delivery.status = "cancelled" if event.status == "cancelled" else "failed"
            request = self.db.get(DeliveryRequest, delivery.delivery_request_id)
            if request is not None and delivery.status == "cancelled" and order.status in {"ready_for_delivery", "shipped", "ready_for_pickup"}:
                request.status = "requested"
            record_event(self.db, delivery=delivery, event_type=f"courier_{event.status}", courier=delivery.provider,
                         note=(event.note or "")[:200] or None)
            self.db.add(Notification(recipient_user_id=order.seller_user_id, channel="in_app",
                                     event_type=f"dispatch.courier_{event.status}", title="Courier delivery problem",
                                     body=f"The courier reported '{event.status}' for order {order.order_number}."))
            return "applied"
        target = DELIVERY_STATE.get(event.status)
        if target is None:
            return "ignored"
        if PROGRESS[target] <= PROGRESS.get(delivery.status, -1):
            return "ignored"  # never move backwards or repeat a step
        now = utcnow()
        if target == "in_transit" and delivery.status == "assigned":
            self._move(order, delivery, "picked-up", now, event)
            return "applied"
        if target == "delivered":
            if delivery.status == "assigned":
                self._move(order, delivery, "picked-up", now, event)  # a courier may skip straight to delivered
            self._move(order, delivery, "delivered", now, event)
            return "applied"
        return "ignored"

    def _move(self, order, delivery, action, now, event):
        rule = STATUS_ACTIONS.get((order.order_type, action))
        if rule is None:
            return
        expected_order, _, new_order, new_delivery, stamp = rule
        delivery.status = new_delivery
        if action == "picked-up":
            delivery.picked_up_at = now
            order.shipped_at = order.shipped_at or now
        else:
            delivery.delivered_at = now
            if event.proof_of_delivery_url:
                delivery.proof_of_delivery_url = event.proof_of_delivery_url[:1024]
        if order.status in expected_order:
            previous = order.status
            order.status = new_order
            setattr(order, stamp, now)
            self.db.add(OrderTimelineEntry(order_id=order.id, from_status=previous, to_status=new_order,
                                           note=f"Courier {delivery.provider}: {event.status.replace('_', ' ')}"))
            for user_id in {order.buyer_user_id, order.seller_user_id}:
                self.db.add(Notification(recipient_user_id=user_id, channel="in_app", event_type="order." + new_order,
                                         title="Order delivery updated",
                                         body=f"Order {order.order_number} is now {new_order.replace('_', ' ')}."))
        record_event(self.db, delivery=delivery, event_type="picked_up" if action == "picked-up" else "delivered",
                     verified_by=f"courier:{delivery.provider}",
                     **({"proof_of_delivery": True} if event.proof_of_delivery_url else {}))

    def reconcile(self, limit: int = 50) -> int:
        """Poll couriers for deliveries that aren't final, to catch webhooks that never arrived."""
        couriers = enabled_couriers()
        open_rows = (self.db.query(Delivery).filter(Delivery.provider.in_(list(couriers)),
                                                    Delivery.status.in_(["assigned", "in_transit"]))
                     .order_by(Delivery.updated_at).limit(limit).all())
        applied = 0
        for delivery in open_rows:
            try:
                latest = couriers[delivery.provider].status(delivery.provider_tracking_reference)
            except CourierError:
                continue
            if latest is not None and self.handle_event(delivery.provider, latest) == "applied":
                applied += 1
        return applied

    def is_final(self, status: str) -> bool:
        return status in FINAL
