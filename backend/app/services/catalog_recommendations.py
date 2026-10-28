"""Deterministic, catalog-grounded commerce recommendations.

Only server-provided verified catalog records may be recommended. This module
does not guess products, invent stock/prices, call an LLM or authorize orders.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable


@dataclass(frozen=True)
class CatalogSuggestion:
    product_id: str
    title: str
    price_ngn: Decimal
    category: str
    available_units: int


def recommend_catalog_items(*, catalog: Iterable[dict], budget_ngn,
                            category: str | None = None, limit: int = 5
                            ) -> list[CatalogSuggestion]:
    try:
        budget = Decimal(str(budget_ngn))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise ValueError("Invalid shopping budget") from exc
    if not budget.is_finite() or budget <= 0 or not 1 <= limit <= 20:
        raise ValueError("Invalid shopping budget or limit")
    expected = category.casefold().strip() if category else None
    candidates: list[CatalogSuggestion] = []
    seen: set[str] = set()
    for item in catalog:
        if not isinstance(item, dict) or item.get("is_published") is not True:
            continue
        product_id = item.get("id")
        title = item.get("title")
        group = item.get("category")
        units = item.get("available_units")
        if (not isinstance(product_id, str) or not product_id
                or not isinstance(title, str) or not title.strip()
                or not isinstance(group, str) or not group.strip()
                or isinstance(units, bool) or not isinstance(units, int)
                or units <= 0 or product_id in seen):
            continue
        try:
            price = Decimal(str(item.get("price_ngn")))
        except (ValueError, TypeError, InvalidOperation):
            continue
        if (not price.is_finite() or price <= 0 or price > budget
                or price.as_tuple().exponent < -2):
            continue
        if expected and group.casefold().strip() != expected:
            continue
        seen.add(product_id)
        candidates.append(CatalogSuggestion(product_id, title.strip(), price,
                                             group.strip(), units))
    return sorted(candidates, key=lambda x: (x.price_ngn, x.product_id))[:limit]
