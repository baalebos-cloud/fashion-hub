# Vendor stock reservations

This phase connects vendor-owned catalog publishing/restock, professional carts, one-vendor checkout, order price review and verified payment callbacks. Stock allocation joins the existing atomic payment/outbox flow. It remains a development milestone, not a global-market launch declaration.

## Release and compatibility

Deploy migration `0005` once with `alembic upgrade head`, then API/worker/frontend versions together. No project database has been accessed by this change. Tests use disposable PostgreSQL/PostGIS databases.

The migration adds foreign keys along the vendor/product/variant/inventory and cart ownership chains, one-active-cart and one-variant-line uniqueness, quantity/counter checks, cart revision, order source/deadline and a durable reservation ledger. It repairs old cart vendor identifiers deterministically from their product's vendor. It refuses orphan records, duplicate active carts/lines, invalid quantities/counters and unattributed pre-existing reserved stock. Resolve reported records explicitly after inspection; do not delete orders or reset stock automatically.

Before upgrading a nonempty environment, back up and inspect counts of each guard condition. Retain legacy initialized payment references for provider reconciliation. New payments require trustworthy vendor catalog provenance; old unpaid carts/orders must be recreated if incompatible. Once reservations or new material orders exist, downgrade refuses to discard that history. An older image does not understand stock expiry/consumption: use a forward fix, or disable material checkout/payment writers and review compatibility before any application rollback.

## Workers and recovery

Set `VENDOR_RESERVATION_TTL_MINUTES` to 1–120 (default 15). Run Celery beat and a worker consuming `payments` (which also runs settlement outbox/reconciliation work):

```sh
celery -A app.workers.celery_app worker -Q payments --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

Beat requests expiry every 30 seconds; each task processes at most 200 orders. One order commits per transaction with `FOR UPDATE SKIP LOCKED`, so overlapping tasks release once. A broker outage cannot lose a checkout reservation: the deadline is in PostgreSQL. Restart beat/workers to drain expired holds. During an outage, stale holds reduce availability conservatively. New payment initialization checks the deadline and releases expired holds itself. Payment settlement also checks it, including after waiting on stock locks.

Lock order is payment → order → sorted inventory for settlement, order → sorted inventory for expiry/cancellation, and buyer account → cart → catalog share locks → sorted inventory for checkout. Expiry/cancellation never take a payment lock. Cart mutations serialize on the buyer account. Restock takes only its inventory row lock. No Celery publish or external notification is part of a checkout/settlement transaction.

Monitor expired unpaid orders, oldest hold age, inventory reserved totals versus active reservation sums, expiry task failures/backlog, and `payment.review` outbox/audit records. If counters disagree, block affected checkout and investigate the ledger; do not set reserved counts to zero. A received payment after release remains successful as a financial fact, while its order is cancelled and its funds require support/refund reconciliation. Never tell the buyer to pay again without checking that reference.

## Verification and limits

Regression coverage uses independent PostgreSQL transactions for two buyers racing for the last unit, duplicate retries, cart mutation versus checkout, and settlement versus cancellation/expiry/failure. Failure injection covers order/settlement rollback and lost commit acknowledgement. HTTP coverage follows vendor profile → admin verification → catalog → cart → order → provider verification → invoice, with ownership rejection. Provider calls are mocked; this does not establish provider sandbox/live readiness.

Checkout uses current server prices; cart prices are estimates and the committed total is reviewed before payment. Tests also cover multiple vendors retaining other cart lines, stale revisions, foreign resources, inactive/unverified catalog, unsupported currency, expired payment initialization, late payment review, additive restock, migration preservation/guards and callback/UI behavior.

Still required before live launch: shipping/tax quotes (currently zero), payment initialization intent/recovery across a provider-success/database-crash window, provider sandbox validation, vendor fulfillment and buyer receipt, refunds/returns and actual KYB operations. Combined vendor payment grouping, additional countries/currencies, load testing, monitoring/backup/restore rehearsal and production rollout are separate phases. Avoid mixed old/new material checkout writers during release.

Restock requests require an `idempotency_key` bound to the vendor account, variant and quantity. The inventory counter and retained restock record commit together; replaying the same intent returns current stock without adding units twice. Changed intent with the same key conflicts. Initial stock on newly created products also has a retained addition record. Pre-migration available stock remains an explicit reconciliation baseline.
