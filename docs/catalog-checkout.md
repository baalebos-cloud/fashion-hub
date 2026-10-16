# Catalog checkout contract and rollout

This phase completes a development/test path for published, made-to-measure designs:

1. A verified active tailor/designer publishes a design with an NGN price and optional required measurement field names.
2. An authenticated customer saves an owned postal address (`POST /api/v1/addresses`) and measurement profile (`POST /api/v1/measurements`). Customer profiles are provisioned lazily when measurements are saved; a profile ID is different from its user/account ID.
3. `POST /api/v1/orders` resolves the professional account, published designs, address ownership and measurement requirements. The request contains identifiers and quantities, never prices or display names.
4. One database commit saves the pending order, aggregated line items, server-owned Decimal prices, delivery/measurement snapshots and its initial timeline entry.
5. Payment initialization locks the order, checks price provenance and ledger totals, and stores the provider authorization URL. Retrying a recorded initialization resumes that session. The callback page shows success only after buyer-authorized server verification, and login preserves the callback reference if the session has expired. Settlement/outbox handling remains as described in [payment recovery](payment-recovery.md).
6. The outbox generates one invoice with the saved line items. Buyer, seller and admins can read it by order or invoice ID. PDF rendering and external notification delivery remain unfinished.

## Breaking API contract

Deploy the matching frontend with the backend. Old clients posting `unit_price`, `name_snapshot`, custom `service` references, missing measurement/address IDs, or no idempotency key receive 422. There is no fallback to a client price.

```json
{
  "professional_user_id": "<seller user UUID, not professional profile UUID>",
  "items": [{"reference_type": "design", "reference_id": "<published design UUID>", "quantity": 1}],
  "delivery_address_id": "<owned Address UUID, not Location UUID>",
  "measurement_profile_id": "<owned MeasurementProfile UUID>",
  "idempotency_key": "<unique client-generated UUID>"
}
```

The key is globally unique, restricted to letters/digits/underscore/hyphen, and at most 128 characters. Reuse it only for the same intent. Canonicalized IDs and aggregated quantities determine the fingerprint. The same buyer/key/intent returns the original record after a lost response, including if prices or publication status subsequently change. A different request or buyer gets 409. The screen retains the key for retries while mounted; applications that need recovery after browser closure should persist the intent/key and reconcile with the orders list before resubmitting.

Requests contain 1–50 lines and 1–100 units per design after aggregation. Only one professional, NGN and Nigerian delivery addresses are supported in this phase. Required measurements must exist with positive values and explicit cm/in units. The new APIs create immutable saved records; editing/deleting addresses and measurement profiles is future work. Private fulfillment snapshots are stored on orders and excluded from ordinary order list/detail DTOs; a dedicated authorized fulfillment view remains to be implemented.

## Migration 0004

Back up the development/test database, inspect its current Alembic revision, and run `alembic upgrade head` once before releasing this backend. Do not run tests against a live database. No project or live database was accessed; CI uses disposable test databases.

The migration adds order provenance/fingerprint/snapshot fields, a foreign key from order items to orders, the previously unmigrated addresses table with account/location foreign keys, a payment authorization URL, and the location columns missing from historical migrations. It retains legacy address columns/data, backfills current address and coordinate fields (from existing PostGIS points), and allows postal addresses without GPS. It aborts if orphan order items exist; repair those explicitly rather than deleting them automatically. It assumes an Alembic-managed schema; unstamped/create_all or manually altered schemas need a separately reviewed adoption plan.

Existing paid orders and initialized payments retain their settlement, verification and reconciliation paths. New payments for legacy customer orders without trustworthy catalog snapshots are blocked; create a replacement catalog order after checking that no previous provider payment exists. Never synthesize prices or mark legacy data as `catalog_v1` to bypass the check. Legacy incomplete addresses remain stored but are omitted from checkout selection.

Downgrade refuses to discard catalog order snapshots or saved addresses once they exist. Prefer a forward fix. An older application image can still create unsafe legacy pending orders, so rolling back the application requires disabling new checkout until a compatible fix is released.

## Limits and next work

This is not a production launch gate. Delivery fees, tax and discounts still default to zero; shipping eligibility, capacity/lead-time reservations and tax calculation must be designed before accepting live orders. Prices are fixed at order creation; pending orders currently have no expiry. Add an explicit quote/acceptance lifecycle for custom work and price changes rather than accepting client-supplied prices. Vendor carts/stock reservations and multiple sellers remain separate unfinished flows.

A provider accepting initialization followed by a timeout or failed database commit is still an ambiguous external effect. Recorded sessions are resumable; provider intent creation itself is not yet crash-safe. Add durable initialization intents and provider idempotency/status recovery before a live-money launch. The order lock prevents concurrent duplicate calls within a healthy transaction but is held during the provider call; load/latency testing is still needed. Callback origins must match `CORS_ALLOWED_ORIGINS`, including scheme and port, and payment provider URLs must use HTTPS.

CI covers actual PostGIS migrations, concurrent order/payment initialization, tampered prices, validation/ownership, changed-intent conflicts, snapshot stability, commit rollback and the authenticated HTTP order→payment→outbox→invoice path with a mocked provider. Frontend tests check payload/account IDs, retry keys and verified/pending/error callback states. Real provider sandboxes, a full browser run, accessibility audit, restore rehearsal and load tests remain separate gates.
