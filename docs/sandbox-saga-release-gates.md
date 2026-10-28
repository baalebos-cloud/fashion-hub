# Sandbox Saga and measurement release notes

## Financial boundary
This change adds **simulation-only** Saga events. An internal `ESCROW_HELD` state
does NOT establish that a payment service provider actually holds customer
funds. The `ledger_entries` journal is a balanced, immutable *internal
simulation*, not a bank or escrow ledger. All real custody, payouts, and
reversals require a provider-issued reference and independent authoritative
verification. Production Saga payments are hard-disabled by
`ENABLE_PRODUCTION_PAYMENTS=False`; existing `PAYMENTS_ENABLED` and
`REFUND_EXECUTION_ENABLED` release gates remain unchanged.

The customer-facing Saga banner is opt-in:
`VITE_SAGA_SANDBOX_UI_ENABLED=true` in a **non-production** preview only.
Its status explicitly says simulated and shows no real refund receipt.

## Compensation and worker behavior
* A stalled paid order becomes `REVIEW_REQUIRED` after 48 hours in a
  staging/test-only Celery sweep. No money moves.
* Missing couriers generate a review-required reassignment event; they never
  automatically refund already purchased fabric.
* Redis dead-letter entries contain task names, exception types and time,
  not customer measurement values or financial secrets.
* A provider timeout is never interpreted as refund success.

## Idempotency and ledger
* Checkout requires matching JSON + HTTP `Idempotency-Key`; authoritative
  `orders.idempotency_key` persists across Redis restarts.
* `POST /api/v1/payments/refund` requires a key stored uniquely on
  `refunds.idempotency_key`. Redis mirrors completed request IDs for 24h;
  the database unique constraint is the real guarantee.
* Legacy `POST /api/v1/refunds` remains available for backwards
  compatibility, but must be migrated before a production API version change.
* Journal rows are protected by PostgreSQL UPDATE/DELETE rejection triggers.

## Measurement privacy
Per-user drafts are stored locally for seven days on the same browser and are
cleared after successful save. This is convenient but not encrypted. Shared
devices should clear drafts and browser storage, and production should offer
an explicit opt-in to persistent sensitive measurements.

## Release gates still outstanding
1. Independent provider escrow/payout contract and legally reviewed custody
   arrangement, tested refund receipts and reconciliation.
2. Full four-actor material acceptance + two-leg delivery Saga with
   idempotent dispatch integration. A review-required courier event is not
   proof of automatic alternative assignment.
3. Isolation evidence for staging PostGIS and Redis, plus authenticated test
   accounts and at least one real provider sandbox requery.
4. Explicit additional approval before production rollout, live payment flags,
   migration on shared data, or worker/beat changes.
