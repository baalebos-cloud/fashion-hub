"""Records shopping activity for learned recommendations.

Two sources feed interaction_events:

* The website sends what only the browser sees: product/design/tailor views, searches and
  started bookings (record_batch). Cart adds, favourites and purchases are NOT accepted from the
  browser, so nobody can fake them.
* sync_history() copies cart adds, favourites and purchases from the platform's own tables. It
  runs daily, is safe to re-run (dedupe keys), and on its first run brings in existing history
  so recommendations have data from day one.

Accounts with personalised recommendations turned off record nothing, and their past activity is
deleted when they turn it off. Everything is deleted after INTERACTION_RETENTION_DAYS.
"""
import re
import uuid
from datetime import timedelta

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timezone import utcnow
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.design import Design
from app.models.favorite import Favorite
from app.models.interaction_event import ITEM_TYPES, InteractionEvent
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product_variant import ProductVariant
from app.models.recommendation_impression import RecommendationImpression
from app.models.professional import Professional
from app.models.user import User
from app.models.vendor_product import VendorProduct

# Events the browser may report. Everything else comes from the platform's own records.
CLIENT_EVENT_TYPES = ("view", "search", "booking_started")
MAX_BATCH = 50
VIEW_DEDUPE_MINUTES = 30
_SOURCE = re.compile(r"^[a-z][a-z_]{0,31}$")
_SPACES = re.compile(r"\s+")
_ITEM_MODELS = {"product": VendorProduct, "design": Design, "professional": Professional}
_FAVORITE_ITEM = {"vendor_product": "product", "design": "design", "professional": "professional"}
# Orders in these states were never really bought.
_NOT_PURCHASED = ("cancelled", "canceled", "failed", "rejected", "refunded", "payment_failed")


def normalize_query(text: str | None) -> str | None:
    if not isinstance(text, str):
        return None
    cleaned = _SPACES.sub(" ", text).strip().lower()[:100]
    return cleaned or None


def _actor_filter(query, user_id, anonymous_id):
    if user_id is not None:
        return query.filter(InteractionEvent.user_id == user_id)
    return query.filter(InteractionEvent.user_id.is_(None), InteractionEvent.anonymous_id == anonymous_id)


def record_batch(db: Session, *, user: User | None, anonymous_id: str | None, events: list[dict]) -> int:
    """Store valid browser events and return how many were kept. Invalid, unknown-item and
    repeated views are dropped silently: the website never needs to retry or react."""
    if user is not None and not user.personalization_enabled:
        return 0
    if user is None and not anonymous_id:
        return 0
    user_id = user.id if user is not None else None
    now = utcnow()

    candidates = []
    for event in events[:MAX_BATCH]:
        kind = event.get("event_type")
        if kind not in CLIENT_EVENT_TYPES:
            continue
        source = event.get("source")
        source = source if isinstance(source, str) and _SOURCE.match(source) else None
        if kind == "search":
            query = normalize_query(event.get("search_query"))
            if query:
                candidates.append(dict(event_type=kind, item_type=None, item_id=None,
                                       search_query=query, source=source))
            continue
        item_type, item_id = event.get("item_type"), event.get("item_id")
        if item_type not in ITEM_TYPES or not isinstance(item_id, uuid.UUID):
            continue
        candidates.append(dict(event_type=kind, item_type=item_type, item_id=item_id,
                               search_query=None, source=source))

    # Drop events for items that don't exist (one query per item type).
    existing: set[tuple[str, uuid.UUID]] = set()
    for item_type, model in _ITEM_MODELS.items():
        ids = {c["item_id"] for c in candidates if c["item_type"] == item_type}
        if ids:
            existing |= {(item_type, row[0]) for row in db.query(model.id).filter(model.id.in_(ids))}

    # A view of the same item by the same person counts once per VIEW_DEDUPE_MINUTES.
    recent_views = set()
    viewed = {(c["item_type"], c["item_id"]) for c in candidates if c["event_type"] == "view"}
    if viewed:
        since = now - timedelta(minutes=VIEW_DEDUPE_MINUTES)
        rows = _actor_filter(db.query(InteractionEvent.item_type, InteractionEvent.item_id),
                             user_id, anonymous_id).filter(
            InteractionEvent.event_type == "view", InteractionEvent.occurred_at >= since,
            InteractionEvent.item_id.in_({item_id for _, item_id in viewed}))
        recent_views = {(row[0], row[1]) for row in rows}

    kept = 0
    for c in candidates:
        if c["item_id"] is not None:
            key = (c["item_type"], c["item_id"])
            if key not in existing:
                continue
            if c["event_type"] == "view":
                if key in recent_views:
                    continue
                recent_views.add(key)
        db.add(InteractionEvent(user_id=user_id, anonymous_id=anonymous_id, occurred_at=now, **c))
        kept += 1
    db.commit()
    return kept


def set_personalization(db: Session, user: User, enabled: bool) -> bool:
    """Turn personalised recommendations on or off. Turning it off deletes the account's
    recorded activity straight away."""
    user.personalization_enabled = enabled
    if not enabled:
        db.query(InteractionEvent).filter(InteractionEvent.user_id == user.id).delete(synchronize_session=False)
        db.query(RecommendationImpression).filter(RecommendationImpression.user_id == user.id).delete(
            synchronize_session=False)
    db.commit()
    return enabled


def purge_expired(db: Session) -> int:
    cutoff = utcnow() - timedelta(days=settings.INTERACTION_RETENTION_DAYS)
    deleted = (db.query(InteractionEvent).filter(InteractionEvent.occurred_at < cutoff)
               .delete(synchronize_session=False))
    deleted += (db.query(RecommendationImpression).filter(RecommendationImpression.served_at < cutoff)
                .delete(synchronize_session=False))
    db.commit()
    return deleted


def _history_rows(db: Session, cutoff):
    """Cart adds, favourites and purchases from the platform's own tables, newest
    INTERACTION_RETENTION_DAYS only, for accounts that allow personalisation."""
    allowed = User.personalization_enabled.is_(True)

    favorites = (db.query(Favorite).join(User, User.id == Favorite.user_id)
                 .filter(allowed, Favorite.created_at >= cutoff))
    for fav in favorites:
        item_type = _FAVORITE_ITEM.get(fav.favorite_type)
        if item_type:
            yield dict(user_id=fav.user_id, event_type="favorite", item_type=item_type,
                       item_id=fav.favorite_ref_id, occurred_at=fav.created_at,
                       dedupe_key=f"history:favorite:{fav.id}")

    cart_adds = (db.query(CartItem.id, Cart.owner_user_id, ProductVariant.product_id, CartItem.created_at)
                 .join(Cart, Cart.id == CartItem.cart_id)
                 .join(ProductVariant, ProductVariant.id == CartItem.product_variant_id)
                 .join(User, User.id == Cart.owner_user_id)
                 .filter(allowed, CartItem.created_at >= cutoff))
    for item_id, owner, product_id, created in cart_adds:
        yield dict(user_id=owner, event_type="add_to_cart", item_type="product", item_id=product_id,
                   occurred_at=created, dedupe_key=f"history:cart:{item_id}")

    orders = (db.query(Order).join(User, User.id == Order.buyer_user_id)
              .filter(allowed, Order.created_at >= cutoff, Order.status.notin_(_NOT_PURCHASED)))
    for order in orders:
        when = order.ordered_at or order.created_at
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        variant_ids = [i.reference_id for i in items if i.reference_type == "product_variant" and i.reference_id]
        products = dict(db.query(ProductVariant.id, ProductVariant.product_id)
                        .filter(ProductVariant.id.in_(variant_ids))) if variant_ids else {}
        for line in items:
            if line.reference_type == "design" and line.reference_id:
                item_type, item_id = "design", line.reference_id
            elif line.reference_type == "product_variant" and line.reference_id in products:
                item_type, item_id = "product", products[line.reference_id]
            else:
                continue
            yield dict(user_id=order.buyer_user_id, event_type="purchase", item_type=item_type,
                       item_id=item_id, occurred_at=when, dedupe_key=f"history:order_item:{line.id}")
        professional = (db.query(Professional.id).filter(Professional.user_id == order.seller_user_id)
                        .scalar())
        if professional is not None:
            yield dict(user_id=order.buyer_user_id, event_type="purchase", item_type="professional",
                       item_id=professional, occurred_at=when, dedupe_key=f"history:order:{order.id}")


def sync_history(db: Session, batch_size: int = 500) -> int:
    """Copy cart adds, favourites and purchases into interaction_events. Idempotent."""
    cutoff = utcnow() - timedelta(days=settings.INTERACTION_RETENTION_DAYS)
    inserted = 0
    batch: list[dict] = []

    def flush():
        nonlocal inserted
        if not batch:
            return
        statement = (insert(InteractionEvent.__table__)
                     .values([dict(id=uuid.uuid4(), source="history", anonymous_id=None,
                                   search_query=None, **row) for row in batch])
                     .on_conflict_do_nothing(index_elements=["dedupe_key"])
                     .returning(InteractionEvent.__table__.c.id))
        inserted += len(db.execute(statement).fetchall())
        batch.clear()

    for row in _history_rows(db, cutoff):
        if row["occurred_at"] is None:
            continue
        batch.append(row)
        if len(batch) >= batch_size:
            flush()
    flush()
    db.commit()
    return inserted
