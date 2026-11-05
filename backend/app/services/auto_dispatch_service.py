"""Sequential auto-offers (phase 3), behind DISPATCH_AUTO_OFFER_ENABLED.

A new job is offered to one rider at a time with an exclusive window
(DISPATCH_AUTO_OFFER_TTL_SECONDS). Decline, expiry or going offline moves it to
the next-ranked rider; after DISPATCH_AUTO_OFFER_MAX_ATTEMPTS, or when nobody
is eligible, the job simply stays on the open job board.

Eligibility (deterministic, no ML): verified, online, has a vehicle, no active
delivery, not already offered this job, and within the radius when a base
location is known. Ranking: straight-line distance from the rider's base
(current location, else verified home address) to pickup, then rating, then
completed deliveries; riders with no known base rank last. Distances are for
ranking only and never shown as an ETA. Rider locations never leave the server.

Expiry is driven by a Celery beat sweep and also checked lazily on every read,
so offers still advance if the scheduler is down.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.timezone import utcnow
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.dispatch_job_offer import DispatchJobOffer
from app.models.location import Location
from app.models.notification import Notification
from app.models.order import Order
from app.models.user import User
from app.services.dispatch_routing import estimate_straight_line_km, validate_point
from app.services.internal_courier_service import InternalCourierService, is_dispatchable

logger = get_logger(__name__)
ACTIVE_DELIVERY_STATUSES = ("assigned", "picked_up", "in_transit", "out_for_delivery")


def auto_offers_enabled() -> bool:
    return bool(settings.DISPATCH_AUTO_OFFER_ENABLED)


def _point(location: Location | None):
    if location is None:
        return None
    try:
        return validate_point(location.latitude, location.longitude)
    except Exception:  # noqa: BLE001 - a bad pin just means "location unknown".
        return None


class AutoDispatchService:
    def __init__(self, db: Session):
        self.db = db

    # ---- reads ----------------------------------------------------------------
    def live_offer(self, request_id) -> DispatchJobOffer | None:
        return (self.db.query(DispatchJobOffer)
                .filter(DispatchJobOffer.delivery_request_id == request_id,
                        DispatchJobOffer.status == "offered", DispatchJobOffer.expires_at > utcnow())
                .first())

    def held_by_other(self, request_id, partner_id) -> bool:
        """True while another rider holds this job's exclusive window."""
        offer = self.live_offer(request_id)
        return offer is not None and offer.delivery_partner_id != partner_id

    def held_request_ids(self, exclude_partner_id=None) -> set:
        query = self.db.query(DispatchJobOffer.delivery_request_id).filter(
            DispatchJobOffer.status == "offered", DispatchJobOffer.expires_at > utcnow())
        if exclude_partner_id is not None:
            query = query.filter(DispatchJobOffer.delivery_partner_id != exclude_partner_id)
        return {row[0] for row in query.all()}

    def offers_for_partner(self, partner_id) -> list[DispatchJobOffer]:
        if not auto_offers_enabled():
            return []  # flag off: reservations are void, the open board is the only path
        self.advance_expired()
        return (self.db.query(DispatchJobOffer)
                .filter(DispatchJobOffer.delivery_partner_id == partner_id,
                        DispatchJobOffer.status == "offered", DispatchJobOffer.expires_at > utcnow())
                .order_by(DispatchJobOffer.expires_at).all())

    # ---- ranking --------------------------------------------------------------
    def _base_location(self, partner: DeliveryPartner, user: User):
        if partner.current_location_id:
            point = _point(self.db.get(Location, partner.current_location_id))
            if point:
                return point
        if user.home_location_id:
            return _point(self.db.get(Location, user.home_location_id))
        return None

    def ranked_candidates(self, request: DeliveryRequest) -> list[tuple[DeliveryPartner, float | None]]:
        already = self.db.query(DispatchJobOffer.delivery_partner_id).filter(
            DispatchJobOffer.delivery_request_id == request.id)
        busy = self.db.query(Delivery.delivery_partner_id).filter(
            Delivery.status.in_(ACTIVE_DELIVERY_STATUSES), Delivery.delivery_partner_id.is_not(None))
        # One live reservation per rider, so accepting one job never leaves others stranded.
        reserving = self.db.query(DispatchJobOffer.delivery_partner_id).filter(
            DispatchJobOffer.status == "offered", DispatchJobOffer.expires_at > utcnow())
        rows = (self.db.query(DeliveryPartner, User).join(User, User.id == DeliveryPartner.user_id)
                .filter(DeliveryPartner.is_verified.is_(True), DeliveryPartner.is_available.is_(True),
                        DeliveryPartner.vehicle_type.is_not(None), User.is_active.is_(True),
                        DeliveryPartner.id.notin_(already), DeliveryPartner.id.notin_(busy),
                        DeliveryPartner.id.notin_(reserving))
                .all())
        if not rows:
            return []
        completed = dict(self.db.query(Delivery.delivery_partner_id, func.count(Delivery.id))
                         .filter(Delivery.status == "delivered",
                                 Delivery.delivery_partner_id.in_([p.id for p, _ in rows]))
                         .group_by(Delivery.delivery_partner_id).all())
        pickup = _point(self.db.get(Location, request.pickup_location_id))
        scored = []
        for partner, user in rows:
            base = self._base_location(partner, user)
            distance = estimate_straight_line_km(base, pickup) if base and pickup else None
            if distance is not None and distance > settings.DISPATCH_AUTO_OFFER_RADIUS_KM:
                continue
            scored.append((partner, distance, float(partner.average_rating or 0), int(completed.get(partner.id, 0))))
        # Known distance first (nearest), then rating, then experience; stable on id.
        scored.sort(key=lambda s: (s[1] is None, s[1] if s[1] is not None else 0, -s[2], -s[3], str(s[0].id)))
        return [(partner, distance) for partner, distance, _, _ in scored]

    # ---- writes ---------------------------------------------------------------
    def offer_next(self, request_id) -> DispatchJobOffer | None:
        """Offer the job to the next-ranked rider. Idempotent and safe to call concurrently."""
        if not auto_offers_enabled():
            return None
        request = (self.db.query(DeliveryRequest).filter_by(id=request_id)
                   .with_for_update().populate_existing().first())
        order = self.db.get(Order, request.order_id) if request else None
        if request is None or request.status != "requested" or not is_dispatchable(order):
            self.db.rollback()
            return None
        existing = self.live_offer(request.id)
        if existing is not None:
            self.db.rollback()
            return existing
        attempts = self.db.query(func.count(DispatchJobOffer.id)).filter(
            DispatchJobOffer.delivery_request_id == request.id).scalar() or 0
        if attempts >= settings.DISPATCH_AUTO_OFFER_MAX_ATTEMPTS:
            self.db.rollback()
            return None  # falls back to the open job board
        candidates = self.ranked_candidates(request)
        if not candidates:
            self.db.rollback()
            return None
        partner, distance = candidates[0]
        offer = DispatchJobOffer(delivery_request_id=request.id, delivery_partner_id=partner.id,
                                 status="offered", attempt=attempts + 1, distance_km=distance,
                                 expires_at=utcnow() + timedelta(seconds=settings.DISPATCH_AUTO_OFFER_TTL_SECONDS))
        self.db.add(offer)
        self.db.add(Notification(
            recipient_user_id=partner.user_id, channel="in_app", event_type="dispatch.job_offered",
            title="New delivery job for you",
            body=f"A job near you is reserved for you for {settings.DISPATCH_AUTO_OFFER_TTL_SECONDS} seconds. "
                 "Open Delivery jobs to accept or decline."))
        try:
            self.db.commit()
        except IntegrityError:
            # Another worker created the live offer first; theirs wins.
            self.db.rollback()
            return self.live_offer(request_id)
        self.db.refresh(offer)
        return offer

    def advance_expired(self) -> int:
        """Expire lapsed offers and move each job to its next rider. Returns offers expired."""
        if not auto_offers_enabled():
            return 0
        lapsed = (self.db.query(DispatchJobOffer)
                  .filter(DispatchJobOffer.status == "offered", DispatchJobOffer.expires_at <= utcnow())
                  .with_for_update(skip_locked=True).all())
        request_ids = []
        for offer in lapsed:
            offer.status = "expired"
            offer.responded_at = utcnow()
            request_ids.append(offer.delivery_request_id)
        self.db.commit()
        for request_id in dict.fromkeys(request_ids):
            try:
                self.offer_next(request_id)
            except Exception as exc:  # noqa: BLE001 - one bad job must not stall the sweep.
                self.db.rollback()
                logger.warning("auto_dispatch_advance_failed", extra={"error_type": type(exc).__name__})
        return len(lapsed)

    def _check_owner(self, offer_id, actor: User) -> DispatchJobOffer:
        """Ownership check WITHOUT locks; callers lock rows in the shared order afterwards."""
        offer = self.db.get(DispatchJobOffer, offer_id)
        partner = self.db.get(DeliveryPartner, offer.delivery_partner_id) if offer else None
        if offer is None or partner is None or str(partner.user_id) != str(actor.id):
            raise NotFoundError("Job offer not found.")
        return offer

    def _lock_offer(self, offer_id) -> DispatchJobOffer:
        return (self.db.query(DispatchJobOffer).filter_by(id=offer_id)
                .with_for_update().populate_existing().one())

    # Lock order everywhere: delivery partner -> delivery request -> job offer, matching
    # InternalCourierService.accept()/assign(), so concurrent accepts conflict instead of deadlocking.
    def accept(self, *, offer_id, actor: User) -> Delivery:
        if not auto_offers_enabled():
            raise ConflictError("Reserved jobs are switched off. Check Delivery jobs for open work.")
        offer = self._check_owner(offer_id, actor)
        if offer.status != "offered" or offer.expires_at <= utcnow():  # cheap pre-check; re-checked under lock
            raise ConflictError("This offer has expired. Check Delivery jobs for open work.")
        courier = InternalCourierService(self.db)
        partner = courier._verified_available_partner(actor)  # 1. partner
        request = (self.db.query(DeliveryRequest).filter_by(id=offer.delivery_request_id)  # 2. request
                   .with_for_update().populate_existing().first())
        offer = self._lock_offer(offer_id)  # 3. offer
        if offer.status != "offered" or offer.expires_at <= utcnow():
            raise ConflictError("This offer has expired. Check Delivery jobs for open work.")
        order = self.db.get(Order, request.order_id) if request else None
        if request is None or request.status != "requested" or not is_dispatchable(order):
            offer.status = "withdrawn"
            self.db.commit()
            raise ConflictError("This job is no longer available.")
        offer.status = "accepted"
        offer.responded_at = utcnow()
        return courier.assign(request=request, order=order, partner=partner, fee=request.proposed_fee)

    def decline(self, *, offer_id, actor: User) -> None:
        offer = self._check_owner(offer_id, actor)
        request_id = offer.delivery_request_id
        (self.db.query(DeliveryRequest).filter_by(id=request_id)  # request before offer
         .with_for_update().populate_existing().first())
        offer = self._lock_offer(offer_id)
        if offer.status != "offered":
            raise ConflictError("This offer is no longer open.")
        offer.status = "declined"
        offer.responded_at = utcnow()
        self.db.commit()
        self.offer_next(request_id)

    def withdraw_for_partner(self, partner_id) -> None:
        """A rider going offline releases any job reserved for them to the next rider."""
        if not auto_offers_enabled():
            return
        offers = (self.db.query(DispatchJobOffer)
                  .filter(DispatchJobOffer.delivery_partner_id == partner_id, DispatchJobOffer.status == "offered")
                  .with_for_update().all())
        request_ids = [o.delivery_request_id for o in offers]
        for offer in offers:
            offer.status = "withdrawn"
            offer.responded_at = utcnow()
        self.db.commit()
        for request_id in request_ids:
            self.offer_next(request_id)

    def admin_status(self, request_ids) -> dict:
        """Live offer per job for the dispatch board: rider first name, expiry, attempt."""
        if not request_ids:
            return {}
        rows = (self.db.query(DispatchJobOffer, User)
                .join(DeliveryPartner, DeliveryPartner.id == DispatchJobOffer.delivery_partner_id)
                .join(User, User.id == DeliveryPartner.user_id)
                .filter(DispatchJobOffer.delivery_request_id.in_(request_ids),
                        DispatchJobOffer.status == "offered", DispatchJobOffer.expires_at > utcnow()).all())
        return {offer.delivery_request_id: {
            "offered_to": ((user.full_name or "").strip().split(" ")[0] or "Rider"),
            "offer_expires_at": offer.expires_at, "offer_attempt": offer.attempt} for offer, user in rows}
