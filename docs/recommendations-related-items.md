# Recommendations, part 2: related items

"You might also like" on product pages and "Often bought together" in the materials cart, learned
from the shopping activity recorded in part 1 (`docs/recommendations-activity.md`).

## How items become related (`services/similarity_service.py`, nightly)

1. Each shopper (account, or browser ID when signed out) gets a weight per item from what they did:
   purchase 5, cart add 3, favourite 3, started booking 2, view 1. Weights halve every 30 days
   (`SIMILARITY_HALF_LIFE_DAYS`) and are capped per shopper and item.
2. Two items of the same type are related when the same shoppers engaged with both. The score is
   a cosine similarity (0–1), so popular items don't relate to everything.
3. A pair needs at least 2 different shoppers (`SIMILARITY_MIN_SUPPORT`), so one person or one
   bot can't create a recommendation.

Two signals: `viewed_together` (all activity) and `bought_together` (cart adds and purchases
only). Top 20 per item (`SIMILARITY_TOP_N`) are stored in `item_similarities`; the table is
rebuilt in one transaction. Activity from the last 90 days is used (`SIMILARITY_LOOKBACK_DAYS`).
Similarities are built for products, designs and tailors; this PR shows products only.

## Serving (`services/related_items_service.py`)

- `GET /api/v1/recommendations/products/{id}/similar` — both signals.
- `GET /api/v1/recommendations/products/bought-together?product_id=…` — cart: bought_together only,
  scores summed across cart items, cart items excluded.

Learned matches come first; if there are too few, the row is topped up with fallbacks: same
category within 50–150% of the price (closest first), then the same shop. Each item carries a
`reason` and `learned` flag, and the page labels it ("Often bought together", "Shoppers also
viewed", "Similar item", "From the same shop"). Only buyable items are returned: active, from an
active verified vendor, in NGN, with stock.

Links from a row add `?from=similar_items` / `?from=bought_together`; the product page records
that as the view's source, so part 3 can measure whether suggestions get used.

Migration `0032`. Cart summary items now include `product_id`.
