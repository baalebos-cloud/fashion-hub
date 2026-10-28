# Four-party lifecycle and financial safety review

## Existing state machines
The application has *two* persisted order types: customer clothing orders
(pending -> paid -> accepted -> in_production -> ready_for_delivery -> shipped
-> out_for_delivery -> delivered -> received -> completed), and vendor
material orders (cart -> checkout -> payment_pending -> paid -> confirmed
-> processing -> ready_for_pickup -> picked_up -> in_transit -> delivered
-> received -> completed). Both can enter permitted terminal cancellation /
refund states subject to service-specific rules. Do not rename existing
persisted values as a shortcut to an idealized unified Saga.

## Scope of this change
Migration 0009 rejects unknown combinations of order_type and status
at the database layer, and aborts if historical records need reconciliation.
The existing service-layer transition and actor-authorization rules remain
the authoritative guards against illegal *edges* between permitted states.
A check constraint alone cannot enforce every state transition.

## Four-party Saga gap
A single atomic transaction cannot cover customer payment, vendor sourcing,
two physical deliveries, and remote provider transfers. The application
does not yet persist an authoritative parent-child relationship between a
customer clothing order and the tailor's material purchase order.
Before enabling four-party autonomous fulfillment:
1. Add a reviewed parent customer-order reference and immutable material
   request acceptance, with ownership and vendor stock reservation.
2. Record courier assignments and proof-of-delivery separately for the fabric
   leg and the finished-garment leg. Require verified available couriers.
3. Make each downstream step idempotent, append audit/timeline entries, and
   compensate a failed step without silently reversing completed physical work.
4. Define cancellation windows, partial-failure handling, merchant settlement
   rights, dispute evidence, and who bears delivery/refund fees.

## Escrow and refunds are a release block
The existing payment recovery outbox protects local ledger mutations and
records review-required payments. It is **not a licensed third-party escrow
facility**. A database flag cannot create custody or reverse a provider
transaction. Do not promise automatic refunds or escrow until the payment
provider contract, funds-flow authorizations, payout release rules, and
jurisdiction-specific legal review permit it.

For now, any paid order cancelled after a verified charge must be marked
for reconciliation/review using the existing payment flow; never delete a
paid payment, roll back an external charge with SQL, or credit a refund
without a confirmed provider reversal. Keep production payments disabled
until an independently approved implementation and sandbox evidence exist.

## Staging rollout
- Review historical status values, database backup and Alembic history.
- Upgrade a disposable PostGIS database first. CI must exercise one-step
  downgrade/re-upgrade with no production data.
- On staging, stop workers before applying a first-time data-sensitive
  migration; verify status distribution and reconciliation records.
- Keep staging and production database/Redis resources isolated.
- Do not auto-merge or enable live checkout.
