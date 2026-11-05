"""Shareable recipient tracking (GrabExpress-style), phase 4.

Security model:
- Tokens are 256-bit `secrets.token_urlsafe(32)`; only their SHA-256 hash is stored,
  and the raw token is returned once, at creation.
- Scoped to one order, created only by its buyer, revocable, expiring after
  TRACKING_LINK_TTL_HOURS or TRACKING_LINK_AFTER_DELIVERY_HOURS after delivery,
  whichever comes first; at most TRACKING_LINK_MAX_ACTIVE live links per order.
- Invalid, expired and revoked tokens all get the same 404 (no enumeration signal).
- The public view is deliberately narrow: no handover code, phone numbers, full
  address, GPS coordinates, prices or account details.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.timezone import utcnow
from app.models.delivery_share_link import DeliveryShareLink
from app.models.location import Location
from app.models.order import Order
from app.models.professional import Professional
from app.models.user import User
from app.models.vendor import Vendor

logger = get_logger(__name__)
CLOSED_STATUSES = {"cancelled", "refunded", "rejected", "completed"}
DELIVERED_STATUSES = {"delivered", "received", "completed"}


def _aware(value):
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def share_url(token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/track/{token}"


class ShareLinkService:
    def __init__(self, db: Session):
        self.db = db

    # ---- owner side -----------------------------------------------------------
    def _owned_order(self, order_id, actor: User) -> Order:
        order = self.db.get(Order, order_id)
        if order is None or str(order.buyer_user_id) != str(actor.id):
            raise NotFoundError("Order not found.")
        return order

    def _effective_expiry(self, link: DeliveryShareLink, order: Order):
        expiry = _aware(link.expires_at)
        if order.status in DELIVERED_STATUSES and order.delivered_at:
            # orders.delivered_at is stored without a zone, always in UTC.
            expiry = min(expiry, _aware(order.delivered_at) + timedelta(hours=settings.TRACKING_LINK_AFTER_DELIVERY_HOURS))
        return expiry

    def _is_live(self, link: DeliveryShareLink, order: Order) -> bool:
        return (link.revoked_at is None and order.status not in CLOSED_STATUSES - {"completed"}
                and self._effective_expiry(link, order) > utcnow())

    def create(self, *, order_id, actor: User, label: str | None = None) -> tuple[DeliveryShareLink, str]:
        self._owned_order(order_id, actor)
        # Lock the order so concurrent creates count and revoke against the same link set.
        from app.repositories.order_repository import OrderRepository
        order = OrderRepository(self.db).get_by_id_for_update(order_id)
        if order.status in CLOSED_STATUSES:
            raise ConflictError("Tracking links are only available for orders that are still on their way.")
        live = [link for link in self.db.query(DeliveryShareLink)
                .filter(DeliveryShareLink.order_id == order.id, DeliveryShareLink.revoked_at.is_(None))
                .order_by(DeliveryShareLink.created_at).all() if self._is_live(link, order)]
        while len(live) >= settings.TRACKING_LINK_MAX_ACTIVE:
            live.pop(0).revoked_at = utcnow()  # oldest link stops working
        token = secrets.token_urlsafe(32)
        link = DeliveryShareLink(order_id=order.id, created_by_user_id=actor.id, token_hash=hash_token(token),
                                 label=(label or "").strip()[:60] or None,
                                 expires_at=utcnow() + timedelta(hours=settings.TRACKING_LINK_TTL_HOURS))
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link, token

    def list_for_owner(self, *, order_id, actor: User) -> list[dict]:
        order = self._owned_order(order_id, actor)
        links = (self.db.query(DeliveryShareLink).filter(DeliveryShareLink.order_id == order.id)
                 .order_by(DeliveryShareLink.created_at.desc()).limit(20).all())
        return [{"id": link.id, "label": link.label, "created_at": link.created_at,
                 "expires_at": self._effective_expiry(link, order), "active": self._is_live(link, order),
                 "revoked": link.revoked_at is not None, "access_count": link.access_count,
                 "last_accessed_at": link.last_accessed_at} for link in links]

    def revoke(self, *, order_id, link_id, actor: User) -> None:
        order = self._owned_order(order_id, actor)
        link = self.db.query(DeliveryShareLink).filter_by(id=link_id, order_id=order.id).first()
        if link is None:
            raise NotFoundError("Tracking link not found.")
        if link.revoked_at is None:
            link.revoked_at = utcnow()
            self.db.commit()

    # ---- public side ----------------------------------------------------------
    def public_view(self, token: str) -> dict:
        not_found = NotFoundError("This tracking link isn't valid or has expired.")
        if not token or len(token) < 32 or len(token) > 64:
            raise not_found
        link = self.db.query(DeliveryShareLink).filter_by(token_hash=hash_token(token)).first()
        order = self.db.get(Order, link.order_id) if link else None
        if link is None or order is None or not self._is_live(link, order):
            raise not_found
        link.access_count = (link.access_count or 0) + 1
        link.last_accessed_at = utcnow()
        self.db.commit()

        from app.services.dispatch_marketplace_service import DispatchMarketplaceService
        journey = DispatchMarketplaceService(self.db).build_journey(order, resolve_current=True)
        rider = self._rider_card(order)
        live = journey.get("live") or {}
        return {
            "tracking_number": order.order_number,
            "seller_name": self._seller_name(order),
            "kind": "materials" if order.order_type == "vendor_order" else "garment",
            "status": order.status,
            "delivery_status": journey.get("delivery_status"),
            "dropoff_area": self._dropoff_area(order),
            "milestones": journey["milestones"],
            "eta_minutes": live.get("eta_minutes"),
            "eta_basis": live.get("basis"),
            "rider": rider,
            "link_expires_at": self._effective_expiry(link, order),
        }

    def _seller_name(self, order: Order) -> str:
        pro = self.db.query(Professional).filter_by(user_id=order.seller_user_id).first()
        if pro and pro.business_name:
            return pro.business_name
        vendor = self.db.query(Vendor).filter_by(user_id=order.seller_user_id).first()
        return vendor.business_name if vendor else "Tailora seller"

    def _dropoff_area(self, order: Order) -> str | None:
        snapshot = order.delivery_address_snapshot if isinstance(order.delivery_address_snapshot, dict) else {}
        parts = [snapshot.get("city"), snapshot.get("state_region")]
        if not any(parts) and order.delivery_address_id:
            from app.models.address import Address
            address = self.db.get(Address, order.delivery_address_id)
            location = self.db.get(Location, address.location_id) if address else None
            parts = [location.city, location.state_region] if location else []
        parts = [p for p in parts if p]
        return ", ".join(dict.fromkeys(parts)) or None

    def _rider_card(self, order: Order) -> dict | None:
        from app.models.delivery import Delivery
        from app.models.delivery_partner import DeliveryPartner
        delivery = (self.db.query(Delivery).filter(Delivery.order_id == order.id, Delivery.status != "cancelled")
                    .order_by(Delivery.created_at.desc()).first())
        partner = self.db.get(DeliveryPartner, delivery.delivery_partner_id) if delivery and delivery.delivery_partner_id else None
        user = self.db.get(User, partner.user_id) if partner else None
        if partner is None or user is None:
            return None
        return {"first_name": (user.full_name or "").strip().split(" ")[0] or "Rider",
                "vehicle_type": partner.vehicle_type, "is_verified": bool(partner.is_verified),
                "rating": float(partner.average_rating or 0)}
