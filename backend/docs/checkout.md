# Material checkout

Material carts may contain several vendors. **Each checkout selects one vendor and creates one order with its own payment.** Other vendor lines remain in the cart. Combined checkout payments need a separate payment-group model and are not implemented. Never sum several orders and pay only the first order.

`POST /api/v1/checkout` accepts `cart_id`, `cart_revision`, `vendor_id` (the business profile ID), `delivery_address_id` and a 16–128 character `idempotency_key`. Client prices, totals, buyer IDs and seller IDs are rejected. Active tailors/designers can use their own cart and complete Nigerian delivery address. Checkout resolves variant → product → vendor → vendor user and saves server Decimal prices, product/SKU descriptions and a private delivery snapshot. Currently only NGN/Nigeria is supported; shipping/tax remain zero until separate pricing is implemented.

The account lock serializes cart mutations and checkout. A stale revision returns 409. An exact retry with the same key returns the original order, including after a lost commit acknowledgement; a changed intent or different buyer cannot reuse the key. Selected inventory rows lock in variant-ID order; insufficient stock aborts the transaction. Order, items, reservation records, counters, timeline and removal of selected cart lines commit together. The final order total is shown for review before payment initialization.

Checkout moves quantities from available to reserved. The canonical deadline is `orders.reservation_expires_at` (default 15 minutes). Successful payment consumes the holds in the settlement transaction; cancellation, provider-confirmed failure and expiry release them once. Terminal reservation rows are retained. Late successful payments are recorded as received funds with durable `payment.review` work; they cannot revive a cancelled order or create a seller payout. The verified payment response's `requires_review` flag drives the callback screen.

New payment initialization rejects legacy vendor orders without this checkout's provenance/holds. Existing provider references remain verifiable/reconcilable. A paid order cannot be cancelled through the unpaid cancellation endpoint; refunds and returns require their own reviewed workflow. Vendor fulfillment transitions are not yet implemented and return an explicit conflict instead of using the customer state machine.

See [the stock rollout/runbook](../../docs/vendor-stock-reservations.md) for migration, workers, locks and verification.
