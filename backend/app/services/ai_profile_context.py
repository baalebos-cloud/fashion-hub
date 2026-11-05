"""Signed-in user's own account summary for the Tailora assistant.

The assistant uses this to point people at their real next step (finish
verification, add a shop location, check an order in production) instead of
generic advice. Privacy rules, enforced here and covered by tests:

- Only rows owned by ``user`` are read. Nothing about counterparties.
- Only counts, statuses and the user's first name leave this module. Never
  email, phone, addresses, ID numbers, payment data or other users' names.
- Every lookup is best-effort: a failure drops that line, never the reply.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)

PROFESSIONAL_ROLES = {"tailor", "designer"}
CLOSED_ORDER_STATUSES = {"completed", "cancelled", "rejected", "refunded", "received"}
CLOSED_DELIVERY_STATUSES = {"delivered", "rejected", "cancelled", "failed"}


def _first_name(full_name: str | None) -> str | None:
    if not full_name:
        return None
    first = full_name.strip().split()[0] if full_name.strip() else ""
    # Keep the prompt tidy and stop a crafted name acting as an instruction.
    cleaned = "".join(ch for ch in first if ch.isalpha() or ch in "-'")[:32]
    return cleaned or None


def _latest_status(db: Session, model, owner_column, user_id) -> str | None:
    row = (db.query(model.status).filter(owner_column == user_id)
           .order_by(model.created_at.desc()).first())
    return row[0] if row else None


def _open_order_counts(db: Session, user_id) -> tuple[int, int]:
    from app.models.order import Order

    def count(column) -> int:
        return int(db.query(func.count(Order.id)).filter(
            column == user_id, Order.status.notin_(CLOSED_ORDER_STATUSES)).scalar() or 0)

    return count(Order.buyer_user_id), count(Order.seller_user_id)


def _facts(db: Session, user) -> list[str]:
    role = user.role
    facts: list[str] = []
    name = _first_name(getattr(user, "full_name", None))
    if name:
        facts.append(f"First name: {name}.")
    facts.append(f"Role: {role}.")
    if not getattr(user, "is_email_verified", True):
        facts.append("Email address is not yet confirmed.")

    if role == "customer":
        from app.models.measurement_profile import MeasurementProfile
        saved = db.query(func.count(MeasurementProfile.id)).filter(
            MeasurementProfile.customer_id == user.id).scalar() or 0
        facts.append(f"Saved measurement profiles: {int(saved)}.")
        buying, _ = _open_order_counts(db, user.id)
        facts.append(f"Open orders as a buyer: {buying}.")

    if role in PROFESSIONAL_ROLES:
        from app.models.kyc_verification import KYCVerification
        from app.models.professional import Professional
        pro = db.query(Professional).filter(Professional.user_id == user.id).first()
        if pro is None:
            facts.append("Professional profile has not been created.")
        else:
            facts.append("Profile verified." if pro.is_verified else "Profile not yet verified.")
            if not pro.location_id:
                facts.append("Shop location has not been set.")
            if not pro.accepts_new_orders:
                facts.append("Currently not accepting new orders.")
        kyc = _latest_status(db, KYCVerification, KYCVerification.user_id, user.id)
        facts.append(f"Identity (KYC) check: {kyc or 'not submitted'}.")
        buying, selling = _open_order_counts(db, user.id)
        facts.append(f"Open customer orders to fulfil: {selling}. Open material purchases: {buying}.")

    if role == "vendor":
        from app.models.kyb_verification import KYBVerification
        from app.models.vendor import Vendor
        vendor = db.query(Vendor).filter(Vendor.user_id == user.id).first()
        if vendor is None:
            facts.append("Vendor store has not been created.")
        else:
            facts.append("Store verified." if vendor.is_verified else "Store not yet verified.")
            if not vendor.warehouse_location_id:
                facts.append("Store pickup location has not been set.")
        kyb = _latest_status(db, KYBVerification, KYBVerification.business_owner_user_id, user.id)
        facts.append(f"Business (KYB) check: {kyb or 'not submitted'}.")
        _, selling = _open_order_counts(db, user.id)
        facts.append(f"Open material orders to fulfil: {selling}.")

    if role == "delivery_partner":
        from app.models.delivery import Delivery
        from app.models.delivery_partner import DeliveryPartner
        from app.models.kyc_verification import KYCVerification
        partner = db.query(DeliveryPartner).filter(DeliveryPartner.user_id == user.id).first()
        if partner is None:
            facts.append("Rider profile has not been created.")
        else:
            facts.append("Rider verified." if partner.is_verified else "Rider not yet verified.")
            facts.append("Currently online for jobs." if partner.is_available else "Currently offline for jobs.")
            active = db.query(func.count(Delivery.id)).filter(
                Delivery.delivery_partner_id == partner.id,
                Delivery.status.notin_(CLOSED_DELIVERY_STATUSES)).scalar() or 0
            facts.append(f"Active deliveries: {int(active)}.")
        kyc = _latest_status(db, KYCVerification, KYCVerification.user_id, user.id)
        facts.append(f"Identity (KYC) check: {kyc or 'not submitted'}.")

    return facts


def build_profile_context(db: Session, user) -> str:
    """Return a short system-prompt block describing only this user's account."""
    try:
        facts = _facts(db, user)
    except Exception as exc:  # noqa: BLE001 - context is optional; never block a reply.
        db.rollback()
        logger.warning("tailora_profile_context_unavailable", extra={"error_type": type(exc).__name__})
        facts = [f"Role: {user.role}."]
    return (
        "Signed-in user's own account (use it to suggest their most useful next step; "
        "it describes only this user, never mention other users): " + " ".join(facts)
        + " Address the user by first name only when it reads naturally. "
        "If a check is pending or rejected, or setup is incomplete, point them to the "
        "page that fixes it before anything else."
    )
