"""Catalog-grounded budget guidance. No generative price or availability claims."""
from decimal import Decimal, InvalidOperation
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.vendor import Vendor
from app.services import personal_ranking_service
from app.services.catalog_recommendations import recommend_catalog_items
from app.services.vendor_catalog_service import VendorCatalogService

router = APIRouter(prefix="/ai/commerce", tags=["AI Commerce"])


class _FirstPage:
    page = 1
    page_size = 50
    offset = 0


@router.get("/recommendations")
def recommend_products(
    request: Request,
    budget_ngn: Decimal = Query(gt=0),
    category_id: str | None = None,
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Only orderable products: active verified vendors, active user accounts and NGN listings
    # (vendors still being verified are shown in the marketplace but not suggested here).
    listings = VendorCatalogService(db).list(_FirstPage(), include_unverified=False)["items"]
    records = []
    for product in listings:
        variants = [
            variant for variant in product["variants"]
            if isinstance(variant.get("quantity_available"), int)
            and variant["quantity_available"] > 0
        ]
        if not variants:
            continue
        # Skip malformed prices instead of failing the entire response.
        priced = []
        for variant in variants:
            try:
                value = Decimal(str(variant["price"]))
                if value.is_finite() and value > 0 and value.as_tuple().exponent >= -2:
                    priced.append((value, variant))
            except (KeyError, ValueError, TypeError, InvalidOperation):
                continue
        if not priced:
            continue
        priced.sort(key=lambda pair: pair[0])
        records.append({
            "id": str(product["id"]),
            "title": product["name"],
            "category": str(product.get("category_id") or "uncategorized"),
            "price_ngn": priced[0][0],
            "available_units": sum(v["quantity_available"] for v in variants),
            "is_published": product["is_active"],
            "vendor_id": product["vendor_id"],
        })
    # Rules: cheapest first. Learned: the same in-budget matches, ranked for this shopper.
    assignment = personal_ranking_service.assign(
        current_user, None, tracking=personal_ranking_service.tracking_allowed(request))
    matches = recommend_catalog_items(
        catalog=records, budget_ngn=budget_ngn, category=category_id,
        limit=20 if assignment.learned else limit,
    )
    if assignment.learned and matches:
        vendor_of = {r["id"]: r["vendor_id"] for r in records}
        ratings = dict(db.query(Vendor.id, Vendor.average_rating)
                       .filter(Vendor.id.in_({vendor_of[m.product_id] for m in matches})))
        ranked = personal_ranking_service.score_items(
            db, assignment, "product",
            [(UUID(m.product_id), ratings.get(vendor_of[m.product_id], 0)) for m in matches])
        by_id = {UUID(m.product_id): m for m in matches}
        matches = [by_id[item_id] for item_id, _, _ in ranked]
    result = matches[:limit]
    personal_ranking_service.log_impression(db, assignment, "budget_guide", "product",
                                            [UUID(x.product_id) for x in result])
    return {
        "currency": "NGN",
        "items": [
            {
                "product_id": x.product_id, "title": x.title,
                "price_ngn": str(x.price_ngn), "category": x.category,
                "available_units": x.available_units,
            }
            for x in result
        ],
        "catalog_sample_limit": 50,
        "ranking": assignment.variant,
        "note": "Guidance only. Product availability and order totals are rechecked at checkout.",
    }
