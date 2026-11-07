"""Serves related products: learned matches first, then clearly-labelled fallbacks.

Every suggestion carries a reason so the page can say why it's shown, and `learned` says whether
it came from shoppers' behaviour (item_similarities) or from the simple fallback (same category,
similar price, or same vendor) used when an item has too little history.

Only products a shopper could actually buy are returned: active, from an active verified vendor,
priced in NGN, with at least one variant in stock.
"""
import uuid
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.inventory import Inventory
from app.models.item_similarity import ItemSimilarity
from app.models.product_variant import ProductVariant
from app.models.vendor_product import VendorProduct
from app.services.vendor_catalog_service import VendorCatalogService

FALLBACK_PRICE_BAND = (Decimal("0.5"), Decimal("1.5"))
FALLBACK_POOL = 60


def _buyable(db: Session, product_ids) -> dict:
    """product_id -> (product, vendor, lowest in-stock price) for products a shopper can buy."""
    ids = list(product_ids)
    if not ids:
        return {}
    prices = dict(db.query(ProductVariant.product_id, func.min(ProductVariant.price))
                  .join(Inventory, Inventory.product_variant_id == ProductVariant.id)
                  .filter(ProductVariant.product_id.in_(ids), Inventory.quantity_available > 0)
                  .group_by(ProductVariant.product_id))
    rows = VendorCatalogService(db).query().filter(VendorProduct.id.in_(list(prices))).all() if prices else []
    return {product.id: (product, vendor, prices[product.id]) for product, vendor in rows}


def _card(product, vendor, price, reason: str, learned: bool) -> dict:
    return dict(product_id=product.id, name=product.name, vendor_name=vendor.business_name,
                primary_image_url=product.primary_image_url, price_ngn=float(price), currency=product.currency,
                unit_of_measure=product.unit_of_measure, reason=reason, learned=learned)


def _learned(db: Session, product_ids: list, signals: tuple) -> list[tuple[uuid.UUID, float, str]]:
    """(related_id, combined score, reason) best first. Scores add up across the given products;
    bought_together wins the reason when both signals relate the same pair."""
    totals: dict = {}
    reasons: dict = {}
    rows = (db.query(ItemSimilarity.related_id, ItemSimilarity.score, ItemSimilarity.signal)
            .filter(ItemSimilarity.item_type == "product", ItemSimilarity.item_id.in_(product_ids),
                    ItemSimilarity.signal.in_(signals)))
    for related_id, score, signal in rows:
        if related_id in product_ids:
            continue
        totals[related_id] = totals.get(related_id, 0.0) + score
        if signal == "bought_together" or related_id not in reasons:
            reasons[related_id] = signal
    return sorted(((rid, s, reasons[rid]) for rid, s in totals.items()), key=lambda r: (-r[1], str(r[0])))


def _fallback(db: Session, seeds: list[VendorProduct], exclude: set, limit: int) -> list[dict]:
    """Same category within a similar price range, then the same vendor; closest price first."""
    if limit <= 0 or not seeds:
        return []
    categories = {s.category_id for s in seeds if s.category_id}
    vendors = {s.vendor_id for s in seeds}
    anchor = sum((Decimal(s.base_price) for s in seeds), Decimal(0)) / len(seeds)
    low, high = anchor * FALLBACK_PRICE_BAND[0], anchor * FALLBACK_PRICE_BAND[1]

    picked: list[dict] = []
    for scope in ("category", "vendor"):
        query = VendorCatalogService(db).query().filter(VendorProduct.id.notin_(exclude))
        if scope == "category":
            if not categories:
                continue
            query = query.filter(VendorProduct.category_id.in_(categories),
                                 VendorProduct.base_price.between(low, high))
        else:
            query = query.filter(VendorProduct.vendor_id.in_(vendors))
        pool = query.order_by(func.abs(VendorProduct.base_price - anchor), VendorProduct.id).limit(FALLBACK_POOL).all()
        buyable = _buyable(db, [p.id for p, _ in pool])
        for product, _ in pool:
            if product.id in buyable and product.id not in exclude:
                picked.append(_card(*buyable[product.id], reason="similar" if scope == "category" else "same_vendor",
                                    learned=False))
                exclude.add(product.id)
                if len(picked) >= limit:
                    return picked
    return picked


def _recommend(db: Session, seeds: list[VendorProduct], signals: tuple, limit: int) -> list[dict]:
    seed_ids = [s.id for s in seeds]
    learned = _learned(db, seed_ids, signals)
    buyable = _buyable(db, [rid for rid, _, _ in learned])
    items = [_card(*buyable[rid], reason=reason, learned=True) for rid, _, reason in learned if rid in buyable][:limit]
    exclude = set(seed_ids) | {item["product_id"] for item in items}
    return items + _fallback(db, seeds, exclude, limit - len(items))


def similar_products(db: Session, product_id: uuid.UUID, limit: int = 8) -> list[dict]:
    """'You might also like' for a product page."""
    seed = db.get(VendorProduct, product_id)
    if seed is None:
        raise NotFoundError("Product not found.")
    return _recommend(db, [seed], ("bought_together", "viewed_together"), limit)


def bought_together(db: Session, product_ids: list[uuid.UUID], limit: int = 6) -> list[dict]:
    """'Often bought together' for a cart: learned from cart adds and purchases only."""
    seeds = db.query(VendorProduct).filter(VendorProduct.id.in_(product_ids)).all()
    return _recommend(db, seeds, ("bought_together",), limit) if seeds else []
