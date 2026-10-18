# Vendors

A vendor business profile is distinct from its user account. Products belong to the profile; order seller IDs and payouts refer to the user account.

`GET /vendors/me` returns the current vendor's profile or null. `POST /vendors/me` creates one unverified profile; public callers cannot set verification. Only an administrator can `POST /vendors/{profile_id}/verify`, which records an audit event. This manual decision does not implement provider KYB; administrators must complete their actual verification process before granting it.

`POST /vendor-products` creates an owned NGN product with one generated default SKU and an inventory row. Accepts name, description, base_price, optional category_id and initial_stock (default zero). Products stay private until the vendor is verified; inactive products and inactive/non-vendor accounts are excluded from public discovery. `GET /vendor-products` and `GET /vendor-products/{id}` expose active verified listings and variant prices/available quantities, without reserved counters. Lists are paginated.

`GET /vendor-products/mine` and `GET /vendor-products/{id}/owned` include the vendor's private/inactive products. `PATCH /vendor-products/{id}` changes name, description and active state. Editing prices or adding custom variants is not implemented by this form/API; immutable order snapshots preserve already agreed prices.

`GET /vendor-inventory` exposes only the vendor's stock, names and SKUs. `POST /vendor-inventory/{variant_id}/restock` adds `quantity_to_add` under an inventory row lock. It never overwrites reserved quantities. Requests cannot select another vendor's profile or stock. Inventory totals are bounded at one billion units.

Vendors see sales via `GET /orders?perspective=selling&order_type=vendor_order`. Professionals see purchases with `perspective=buying`. Checkout/payment/expiry are implemented; fulfillment, buyer receipt, refunds and physical returns remain future work. Paid orders cannot use the unpaid cancellation route. See [checkout](checkout.md) and [the rollout runbook](../../docs/vendor-stock-reservations.md).

Restock requests require an `idempotency_key` bound to the vendor account, variant and quantity. The inventory counter and retained restock record commit together; replaying the same intent returns current stock without adding units twice. Changed intent with the same key conflicts. Initial stock on newly created products also has a retained addition record. Pre-migration available stock remains an explicit reconciliation baseline.
