"""Admin dispatch control: cancel, release, reassign, and rider issue handling.

Rules:
- Only deliveries that have NOT been picked up can be released, reassigned or
  cancelled here. Once a rider holds the package, recovery goes through the
  issue workflow (a return-to-sender leg is a later phase).
- History is never rewritten: the released delivery and its request are marked
  "cancelled" and a fresh request (same immutable pickup/drop-off snapshots and
  fee) is created, so every rider's involvement stays traceable.
- The order itself is left ready for pickup; the seller is not penalised.
- Every action takes row locks in the same order as rider transitions
  (order -> delivery -> request -> partner), writes an audit log, an order
  timeline note and in-app notifications. No payment or payout code runs.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.models.audit_log import AuditLog
from app.models.delivery import Delivery
from app.models.delivery_issue import DispatchIssueReport
from app.models.delivery_offer import DeliveryOffer
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.notification import Notification
from app.models.order import Order
from app.models.order_timeline import OrderTimelineEntry
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.services.internal_courier_service import InternalCourierService

logger = get_logger(__name__)

RELEASABLE_DELIVERY_STATUSES = {"assigned"}
# Matches ck_dispatch_issue_status (migration 0013).
ISSUE_STATUSES = {"OPEN", "INVESTIGATING", "RESOLVED", "REROUTED"}
CLOSED_ISSUE_STATUSES = {"RESOLVED", "REROUTED"}


def _first_name(user: User | None) -> str:
    return ((user.full_name or "").strip().split(" ")[0] if user else "") or "Rider"


class DispatchAdminService:
    def __init__(self, db: Session):
        self.db = db

    # ---- helpers ------------------------------------------------------------
    def _audit(self, admin: User, action: str, resource_id, ip: str | None, **metadata):
        self.db.add(AuditLog(actor_user_id=admin.id, action=action, resource_type="dispatch",
                             resource_id=resource_id, ip_address=ip, metadata_json=metadata))

    def _notify(self, user_ids, event_type: str, title: str, body: str):
        for user_id in {u for u in user_ids if u}:
            self.db.add(Notification(recipient_user_id=user_id, channel="in_app",
                                     event_type=event_type, title=title, body=body))

    @staticmethod
    def _reason(reason: str | None) -> str:
        cleaned = (reason or "").strip()
        if len(cleaned) < 5:
            raise ValidationAppError("Give a short reason (at least 5 characters); it's kept in the audit log.")
        return cleaned[:500]

    def _lock_delivery(self, delivery_id):
        initial = self.db.get(Delivery, delivery_id)
        if initial is None:
            raise NotFoundError("Delivery not found.")
        order = OrderRepository(self.db).get_by_id_for_update(initial.order_id)
        delivery = (self.db.query(Delivery).filter_by(id=delivery_id)
                    .with_for_update().populate_existing().one())
        request = (self.db.query(DeliveryRequest).filter_by(id=delivery.delivery_request_id)
                   .with_for_update().populate_existing().one())
        return order, delivery, request

    def _end_assignment(self, *, order, delivery, request, admin, reason, action):
        """Cancel the current rider's run without touching the order's own status."""
        if delivery.status not in RELEASABLE_DELIVERY_STATUSES:
            raise ConflictError("The rider has already collected the package. Resolve it through the issue workflow.")
        partner = (self.db.query(DeliveryPartner).filter_by(id=delivery.delivery_partner_id)
                   .with_for_update().populate_existing().first()) if delivery.delivery_partner_id else None
        delivery.status = "cancelled"
        request.status = "cancelled"
        request.rejection_reason = f"{action}: {reason}"[:1000]
        if partner is not None:
            # A released rider goes offline so a no-show isn't immediately re-offered work.
            partner.is_available = False
        # Problems the old rider reported are handed over with the job, not left open.
        self.db.query(DispatchIssueReport).filter(
            DispatchIssueReport.delivery_id == delivery.id,
            DispatchIssueReport.status.notin_(CLOSED_ISSUE_STATUSES),
        ).update({DispatchIssueReport.status: "REROUTED"}, synchronize_session=False)
        try:
            from app.services.delivery_position import clear_position
            clear_position(delivery.id)
        except Exception as exc:  # noqa: BLE001 - GPS cleanup must not block dispatch control.
            logger.warning("dispatch_admin_gps_clear_failed", extra={"error_type": type(exc).__name__})
        self.db.add(OrderTimelineEntry(order_id=order.id, from_status=order.status, to_status=order.status,
                                       actor_user_id=admin.id, note=f"Dispatch {action} by admin: {reason}"))
        return partner

    def _reopen_request(self, request: DeliveryRequest, fee) -> DeliveryRequest:
        # Repost at the fare already agreed for this run (it may come from an accepted
        # rider offer), not the original suggestion, so a release never re-prices the job.
        fresh = DeliveryRequest(order_id=request.order_id, pickup_location_id=request.pickup_location_id,
                                dropoff_location_id=request.dropoff_location_id,
                                package_description=request.package_description,
                                proposed_fee=fee if fee is not None else request.proposed_fee, status="requested")
        self.db.add(fresh)
        self.db.flush()
        return fresh

    # ---- actions ------------------------------------------------------------
    def release(self, *, delivery_id, admin: User, reason: str, ip: str | None = None):
        """Take the job away from an unresponsive rider and put it back on the job board."""
        reason = self._reason(reason)
        order, delivery, request = self._lock_delivery(delivery_id)
        partner = self._end_assignment(order=order, delivery=delivery, request=request,
                                       admin=admin, reason=reason, action="released")
        fresh = self._reopen_request(request, delivery.delivery_fee)
        self._audit(admin, "dispatch.released", delivery.id, ip, reason=reason,
                    order_id=str(order.id), new_request_id=str(fresh.id))
        self._notify([partner.user_id if partner else None], "dispatch.released", "Delivery reassigned",
                     f"You're no longer assigned to order {order.order_number}.")
        self._notify([order.seller_user_id, order.buyer_user_id], "dispatch.released", "Finding a new rider",
                     f"We're finding a new rider for order {order.order_number}.")
        self.db.commit()
        return fresh

    def reassign(self, *, delivery_id, partner_id, admin: User, reason: str, ip: str | None = None):
        """Dispatcher-selected rider: release the current run and assign a chosen verified, available rider."""
        reason = self._reason(reason)
        order, delivery, request = self._lock_delivery(delivery_id)
        if delivery.delivery_partner_id == partner_id:
            raise ConflictError("That rider is already assigned.")
        new_partner = (self.db.query(DeliveryPartner).filter_by(id=partner_id)
                       .with_for_update().populate_existing().first())
        if new_partner is None or not new_partner.is_verified or not new_partner.is_available:
            raise ConflictError("Choose a verified rider who is online.")
        old_partner = self._end_assignment(order=order, delivery=delivery, request=request,
                                           admin=admin, reason=reason, action="reassigned")
        fresh = self._reopen_request(request, delivery.delivery_fee)
        fresh = self.db.query(DeliveryRequest).filter_by(id=fresh.id).with_for_update().one()
        new_delivery = InternalCourierService(self.db).assign(
            request=fresh, order=order, partner=new_partner, fee=delivery.delivery_fee)
        self._audit(admin, "dispatch.reassigned", delivery.id, ip, reason=reason, order_id=str(order.id),
                    new_delivery_id=str(new_delivery.id), new_partner_id=str(new_partner.id))
        self._notify([old_partner.user_id if old_partner else None], "dispatch.released", "Delivery reassigned",
                     f"You're no longer assigned to order {order.order_number}.")
        self._notify([new_partner.user_id], "dispatch.assigned", "New delivery assigned",
                     f"You've been assigned order {order.order_number}. Open it for the route.")
        self._notify([order.seller_user_id, order.buyer_user_id], "dispatch.reassigned", "New rider assigned",
                     f"A new rider is handling order {order.order_number}.")
        self.db.commit()
        return new_delivery

    def cancel_request(self, *, request_id, admin: User, reason: str, ip: str | None = None):
        """Stop looking for a rider (e.g. seller asked, or order on hold). The seller can request again later."""
        reason = self._reason(reason)
        initial = self.db.get(DeliveryRequest, request_id)
        if initial is None:
            raise NotFoundError("Delivery request not found.")
        order = OrderRepository(self.db).get_by_id_for_update(initial.order_id)
        request = (self.db.query(DeliveryRequest).filter_by(id=request_id)
                   .with_for_update().populate_existing().one())
        if request.status != "requested":
            raise ConflictError("Only requests still looking for a rider can be cancelled here.")
        request.status = "cancelled"
        request.rejection_reason = f"cancelled: {reason}"[:1000]
        self.db.query(DeliveryOffer).filter(DeliveryOffer.delivery_request_id == request.id,
                                            DeliveryOffer.status == "pending").update(
            {DeliveryOffer.status: "declined"}, synchronize_session=False)
        self.db.add(OrderTimelineEntry(order_id=order.id, from_status=order.status, to_status=order.status,
                                       actor_user_id=admin.id, note=f"Rider search cancelled by admin: {reason}"))
        self._audit(admin, "dispatch.request_cancelled", request.id, ip, reason=reason, order_id=str(order.id))
        self._notify([order.seller_user_id], "dispatch.request_cancelled", "Rider search stopped",
                     f"Tailora stopped the rider search for order {order.order_number}: {reason}")
        self.db.commit()
        return request

    def update_issue(self, *, issue_id, admin: User, status: str, note: str | None, ip: str | None = None):
        if status not in {"INVESTIGATING", "RESOLVED"}:
            raise ValidationAppError("Set the issue to INVESTIGATING or RESOLVED.")
        issue = (self.db.query(DispatchIssueReport).filter_by(id=issue_id)
                 .with_for_update().populate_existing().first())
        if issue is None:
            raise NotFoundError("Issue not found.")
        if issue.status in CLOSED_ISSUE_STATUSES:
            raise ConflictError("This issue is already closed.")
        if status == "RESOLVED" and len((note or "").strip()) < 5:
            raise ValidationAppError("Add a resolution note so the rider knows what happened.")
        previous = issue.status
        issue.status = status
        self._audit(admin, f"dispatch.issue_{status.lower()}", issue.id, ip,
                    previous=previous, note=(note or "").strip()[:500] or None)
        self._notify([issue.courier_id], f"dispatch.issue_{status.lower()}", "Issue update",
                     (f"Your report was resolved: {(note or '').strip()[:300]}" if status == "RESOLVED"
                      else "Tailora is looking into the issue you reported."))
        self.db.commit()
        return issue

    # ---- reads --------------------------------------------------------------
    def open_issues(self, limit: int = 100) -> list[dict]:
        rows = (self.db.query(DispatchIssueReport, Delivery, Order, User)
                .join(Delivery, Delivery.id == DispatchIssueReport.delivery_id)
                .join(Order, Order.id == Delivery.order_id)
                .join(User, User.id == DispatchIssueReport.courier_id)
                .filter(DispatchIssueReport.status.notin_(CLOSED_ISSUE_STATUSES))
                .order_by(DispatchIssueReport.created_at).limit(limit).all())
        return [{"id": issue.id, "delivery_id": delivery.id, "order_id": order.id,
                 "order_number": order.order_number, "issue_type": issue.issue_type,
                 "description": issue.description, "status": issue.status,
                 "rider_first_name": _first_name(rider), "delivery_status": delivery.status,
                 "has_photo": bool(issue.photo_evidence_url), "created_at": issue.created_at}
                for issue, delivery, order, rider in rows]

    def available_riders(self, limit: int = 100) -> list[dict]:
        rows = (self.db.query(DeliveryPartner, User).join(User, User.id == DeliveryPartner.user_id)
                .filter(DeliveryPartner.is_verified.is_(True), DeliveryPartner.is_available.is_(True))
                .order_by(DeliveryPartner.average_rating.desc()).limit(limit).all())
        return [{"id": partner.id, "first_name": _first_name(user), "vehicle_type": partner.vehicle_type,
                 "rating": float(partner.average_rating or 0)} for partner, user in rows]

    def open_issue_counts(self, delivery_ids) -> dict:
        if not delivery_ids:
            return {}
        return dict(self.db.query(DispatchIssueReport.delivery_id, func.count(DispatchIssueReport.id))
                    .filter(DispatchIssueReport.delivery_id.in_(delivery_ids),
                            DispatchIssueReport.status.notin_(CLOSED_ISSUE_STATUSES))
                    .group_by(DispatchIssueReport.delivery_id).all())

