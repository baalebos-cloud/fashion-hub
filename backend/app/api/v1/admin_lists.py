"""Read-only admin lists and reports: vendors, delivery partners, payments, invoices, reviews, and the
Reports page. Admin-only, paginated, newest first. No NINs, bank details, addresses or coordinates."""
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.core.timezone import utcnow
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.invoice import Invoice
from app.models.kyb_verification import KYBVerification
from app.models.kyc_verification import KYCVerification
from app.models.order import Order
from app.models.payment import Payment
from app.models.rating import Rating
from app.models.review import Review
from app.models.user import User
from app.models.vendor import Vendor
from app.models.vendor_product import VendorProduct

router = APIRouter(prefix="/admin", tags=["Admin"])
admin = require_roles(Role.ADMIN)


def _page(query, page: int, page_size: int):
    total = query.order_by(None).count()
    return total, query.offset((page - 1) * page_size).limit(page_size).all()


def _iso(value):
    return value.isoformat() if value else None


def _names(db: Session, ids) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {u.id: u for u in db.query(User).filter(User.id.in_(ids)).all()}


@router.get("/vendors")
def list_vendors(verified: bool | None = None, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
                 db: Session = Depends(get_db), _: User = Depends(admin)):
    q = db.query(Vendor)
    if verified is not None:
        q = q.filter(Vendor.is_verified.is_(verified))
    total, rows = _page(q.order_by(Vendor.created_at.desc()), page, page_size)
    owners = _names(db, [v.user_id for v in rows])
    products = dict(db.query(VendorProduct.vendor_id, func.count(VendorProduct.id))
                    .filter(VendorProduct.vendor_id.in_([v.id for v in rows]), VendorProduct.is_active.is_(True))
                    .group_by(VendorProduct.vendor_id).all()) if rows else {}
    return {"total": total, "page": page, "page_size": page_size, "items": [{
        "id": str(v.id), "business_name": v.business_name, "owner_name": owners[v.user_id].full_name if v.user_id in owners else None,
        "owner_email": owners[v.user_id].email if v.user_id in owners else None,
        "is_verified": v.is_verified, "average_rating": float(v.average_rating or 0),
        "active_products": int(products.get(v.id, 0)), "created_at": _iso(v.created_at)} for v in rows]}


@router.get("/delivery-partners")
def list_delivery_partners(verified: bool | None = None, online: bool | None = None, page: int = Query(1, ge=1),
                           page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(admin)):
    q = db.query(DeliveryPartner)
    if verified is not None:
        q = q.filter(DeliveryPartner.is_verified.is_(verified))
    if online is not None:
        q = q.filter(DeliveryPartner.is_available.is_(online))
    total, rows = _page(q.order_by(DeliveryPartner.created_at.desc()), page, page_size)
    users = _names(db, [p.user_id for p in rows])
    delivered = dict(db.query(Delivery.delivery_partner_id, func.count(Delivery.id))
                     .filter(Delivery.delivery_partner_id.in_([p.id for p in rows]), Delivery.status == "delivered")
                     .group_by(Delivery.delivery_partner_id).all()) if rows else {}
    return {"total": total, "page": page, "page_size": page_size, "items": [{
        "id": str(p.id), "name": users[p.user_id].full_name if p.user_id in users else None,
        "email": users[p.user_id].email if p.user_id in users else None,
        "vehicle_type": p.vehicle_type, "is_verified": p.is_verified, "is_available": p.is_available,
        "average_rating": float(p.average_rating or 0), "completed_deliveries": int(delivered.get(p.id, 0)),
        "created_at": _iso(p.created_at)} for p in rows]}


@router.get("/payments")
def list_payments(status: str | None = Query(None, max_length=24), provider: str | None = Query(None, max_length=32),
                  page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
                  db: Session = Depends(get_db), _: User = Depends(admin)):
    q = db.query(Payment, Order).join(Order, Order.id == Payment.order_id)
    if status:
        q = q.filter(Payment.status == status)
    if provider:
        q = q.filter(Payment.provider == provider)
    total, rows = _page(q.order_by(Payment.created_at.desc()), page, page_size)
    buyers = _names(db, [o.buyer_user_id for _, o in rows])
    return {"total": total, "page": page, "page_size": page_size, "items": [{
        "id": str(p.id), "order_id": str(o.id), "order_number": o.order_number, "order_type": o.order_type,
        "buyer_name": buyers[o.buyer_user_id].full_name if o.buyer_user_id in buyers else None,
        "amount": float(p.amount), "currency": p.currency, "provider": p.provider, "status": p.status,
        "reference": p.provider_reference, "paid_at": _iso(p.paid_at), "created_at": _iso(p.created_at)} for p, o in rows]}


@router.get("/invoices")
def list_invoices(payment_status: str | None = Query(None, max_length=24), page: int = Query(1, ge=1),
                  page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(admin)):
    q = db.query(Invoice)
    if payment_status:
        q = q.filter(Invoice.payment_status == payment_status)
    total, rows = _page(q.order_by(Invoice.created_at.desc()), page, page_size)
    people = _names(db, [i.issued_to_user_id for i in rows] + [i.issued_by_user_id for i in rows])
    name = lambda uid: people[uid].full_name if uid in people else None  # noqa: E731
    return {"total": total, "page": page, "page_size": page_size, "items": [{
        "id": str(i.id), "invoice_number": i.invoice_number, "order_id": str(i.order_id),
        "issued_to": name(i.issued_to_user_id), "issued_by": name(i.issued_by_user_id),
        "total_amount": float(i.total_amount), "currency": i.currency, "payment_status": i.payment_status,
        "order_date": _iso(i.order_date), "payment_date": _iso(i.payment_date)} for i in rows]}


@router.get("/reviews")
def list_reviews(max_score: int | None = Query(None, ge=1, le=5), page: int = Query(1, ge=1),
                 page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(admin)):
    """Newest reviews; `max_score` (e.g. 2) shows only low ratings, the ones worth checking."""
    score = (db.query(Rating.review_id, func.avg(Rating.score).label("score"))
             .group_by(Rating.review_id).subquery())
    q = db.query(Review, score.c.score).outerjoin(score, score.c.review_id == Review.id)
    if max_score is not None:
        q = q.filter(score.c.score <= max_score)
    total, rows = _page(q.order_by(Review.created_at.desc()), page, page_size)
    people = _names(db, [r.reviewer_user_id for r, _ in rows] + [r.reviewee_user_id for r, _ in rows])
    orders = {o.id: o.order_number for o in db.query(Order).filter(Order.id.in_([r.order_id for r, _ in rows])).all()} if rows else {}
    name = lambda uid: people[uid].full_name if uid in people else None  # noqa: E731
    return {"total": total, "page": page, "page_size": page_size, "items": [{
        "id": str(r.id), "order_number": orders.get(r.order_id), "reviewer": name(r.reviewer_user_id),
        "reviewee": name(r.reviewee_user_id), "score": round(float(s), 1) if s is not None else None,
        "comment": r.comment, "created_at": _iso(r.created_at)} for r, s in rows]}


@router.get("/reports")
def reports(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db), _: User = Depends(admin)):
    """Order volume, GMV (paid orders) and the verification funnel for the last `days` days."""
    since = utcnow() - timedelta(days=days)
    paid_states = ("paid", "accepted", "in_production", "ready_for_delivery", "shipped", "out_for_delivery",
                   "delivered", "received", "completed", "confirmed", "processing", "ready_for_pickup",
                   "picked_up", "in_transit")
    orders = db.query(Order).filter(Order.ordered_at >= since)

    def count(q):
        return q.order_by(None).count()

    by_type = {}
    for kind in ("customer_order", "vendor_order"):
        scoped = orders.filter(Order.order_type == kind)
        paid = scoped.filter(Order.status.in_(paid_states))
        by_type[kind] = {
            "placed": count(scoped), "paid": count(paid),
            "completed": count(scoped.filter(Order.status.in_(("received", "completed")))),
            "cancelled": count(scoped.filter(Order.status.in_(("cancelled", "rejected", "refunded")))),
            "gmv": float(paid.with_entities(func.coalesce(func.sum(Order.total_amount), 0)).scalar() or 0),
        }
    daily = (db.query(func.date(Order.ordered_at), func.count(Order.id))
             .filter(Order.ordered_at >= since).group_by(func.date(Order.ordered_at))
             .order_by(func.date(Order.ordered_at)).all())

    def funnel(model):
        rows = dict(db.query(model.status, func.count(model.id)).filter(model.created_at >= since)
                    .group_by(model.status).all())
        submitted = sum(rows.values())
        return {"submitted": submitted, "verified": rows.get("verified", 0), "rejected": rows.get("rejected", 0),
                "waiting": rows.get("pending", 0) + rows.get("under_review", 0)}

    return {
        "days": days, "currency": "NGN",
        "garment_orders": by_type["customer_order"], "material_orders": by_type["vendor_order"],
        "gmv": round(by_type["customer_order"]["gmv"] + by_type["vendor_order"]["gmv"], 2),
        "orders_per_day": [{"date": str(d), "orders": int(n)} for d, n in daily],
        "identity_checks": funnel(KYCVerification), "business_checks": funnel(KYBVerification),
    }
