"""Catalog-grounding regression tests for the Seam shopping recommendation core."""
from decimal import Decimal
import pytest

from app.services.catalog_recommendations import recommend_catalog_items


def _item(id="1", price_ngn="1000", category="fabric", available_units=2, is_published=True):
    return dict(id=id, title="Cotton", price_ngn=price_ngn, category=category,
                available_units=available_units, is_published=is_published)


def test_only_published_in_stock_catalog_items_within_budget():
    items = [_item(), _item("2", "900", is_published=False),
             _item("3", "800", available_units=0), _item("4", "1001"),
             _item("5", "500", category="buttons")]
    suggestions = recommend_catalog_items(catalog=items, budget_ngn="1000",
                                          category="fabric")
    assert [item.product_id for item in suggestions] == ["1"]
    assert suggestions[0].price_ngn == Decimal("1000")


def test_filters_invalid_prices_duplicates_and_sorts_deterministically():
    catalog = [_item("a", "NaN"), _item("x", "900"), _item("x", "800"),
               _item("b", "-1"), _item("c", "900.001"), _item("z", "100")]
    suggestions = recommend_catalog_items(catalog=catalog, budget_ngn="1000")
    assert [x.product_id for x in suggestions] == ["z", "x"]


def test_boolean_inventory_is_not_stock():
    assert recommend_catalog_items(catalog=[_item(available_units=True)],
                                   budget_ngn="1000") == []


@pytest.mark.parametrize("budget", ["NaN", "-1", "0", "Infinity", None])
def test_invalid_budget_rejected(budget):
    with pytest.raises(ValueError):
        recommend_catalog_items(catalog=[], budget_ngn=budget)


def test_does_not_mutate_catalog_and_caps_response():
    items = [_item(str(n), str(n + 1)) for n in range(30)]
    original = [x.copy() for x in items]
    result = recommend_catalog_items(catalog=items, budget_ngn=1000, limit=3)
    assert len(result) == 3
    assert items == original


def test_empty_catalog_produces_no_fabricated_recommendations():
    assert recommend_catalog_items(catalog=[], budget_ngn="30000") == []
