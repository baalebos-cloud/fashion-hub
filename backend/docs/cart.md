# Material cart

Each active tailor/designer has at most one active cart. It can contain several vendor profiles; one variant has one line with an integer quantity from 1 to 10,000 (up to 100 different variants). Vendor identity and current price come from the catalog. Adding an item checks availability but does not reserve it.

- `GET /api/v1/carts/summary` returns the owned active cart, revision, named lines and current prices/availability.
- `POST /api/v1/carts/items` accepts `product_variant_id` and `quantity` and returns the summary.
- `PATCH /api/v1/carts/items/{id}` accepts `quantity`; `DELETE` removes the line. Both require ownership of the active cart.

Every mutation increments the cart revision. Cart summaries are advisory: checkout rechecks the catalog and locks stock before creating a hold. Each checkout selects one vendor and leaves the other vendors in the cart. See [checkout](checkout.md).
