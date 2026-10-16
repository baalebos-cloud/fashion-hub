# Migration and payment recovery runbook

This change targets development/test databases, as confirmed by the repository owner. No live database has been read or changed. Do not treat passing test migrations as approval to apply them to an unidentified existing database.

## What changes

`0002` now declares its dependency on `035e1bd61029`, so table alterations cannot run before the initial tables exist. The existing revision identifiers, parent links, and historical SQL are preserved. Migration `0003` follows the existing merge head and adds `payment_outbox` and `payments.last_reconciled_at`, makes invoice order IDs unique, and aligns the payment-event `processed` type to Boolean. It also adds the missing invoice `order_date` column and backfills it from the associated order. The notification `sent_at` model now matches its existing SQL timestamp type. Notification channel/event/metadata columns are added, existing notification types are copied into the new event column, and the legacy type column is retained for compatibility. It accepts both the historical Boolean schema and JSON booleans from development `create_all` databases.

The upgrade checks for duplicate invoices and stops rather than deleting or guessing which invoice to retain. Invalid JSON Boolean values also stop conversion. The new revision does not support offline SQL generation because its guards inspect existing data. Its downgrade refuses to discard unprocessed outbox work.

## Before upgrading

1. Identify the target database and take a recoverable backup, even for useful development data. Stop API writes and workers during this initial rollout. Use the same database URL for the release command and application.
2. From `backend`, run `alembic current` and `alembic heads`. Supported historical paths are an empty database, `0001`, `035e1bd61029`, `0002`, and `2ab23f38e9c6`. The checkout phase also supports upgrades from `0003`; a current upgrade ends at `0004`. Read [the catalog checkout rollout](catalog-checkout.md) for its added schema, data-preserving guards and matching frontend contract.
3. Inspect the current schema. If it was built with `Base.metadata.create_all()` without Alembic history, do not stamp or replay initial table creation against it. For disposable test data, create a new database and run the migrations. If data needs preservation, compare the complete schema with the historical revision before choosing an explicit adoption plan.
4. For a migrated schema, check duplicates and event types:

```sql
SELECT order_id, count(*) FROM invoices GROUP BY order_id HAVING count(*) > 1;
SELECT data_type FROM information_schema.columns
 WHERE table_schema = current_schema()
   AND table_name = 'payment_transactions' AND column_name = 'processed';
-- Valid values are true and false (Boolean or JSON Boolean).
SELECT processed::text, count(*) FROM payment_transactions
 GROUP BY processed::text;
```

Review duplicate invoices manually. Do not delete financial records automatically. Keep a record of the chosen canonical invoice and any migration of references before resolving duplicates. Unknown Alembic heads, manual stamps, missing tables, invalid event values, and duplicated invoice records need investigation before proceeding.

## Upgrade and start

```sh
cd backend
alembic upgrade head
alembic current
# Start the API, a worker that consumes the payments queue, and exactly one beat scheduler.
celery -A app.workers.celery_app worker -Q payments,invoices,notifications,delivery,verification,media,ai,celery --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

Run migrations once as a release step. Do not run independent migrations from every API replica. Existing development Docker Compose startup still runs `alembic upgrade head` for its single API service; use a separate release step when deploying replicas. A PostGIS-capable database and extension-creation privileges are needed for an empty installation. Worker queue routing must include `payments`, not just the default `celery` queue.

After upgrade, verify `/health/ready`, exercise a sandbox payment, confirm one payment/order/payout/timeline transition, and wait for the outbox to produce one invoice and the expected in-app notifications. These are database records; invoice PDF rendering and external notification delivery remain separate unfinished features. This PR intentionally stops automatically enqueueing the existing unimplemented PDF renderer.

## Settlement guarantees and boundaries

- The provider's reference, exact amount, currency, and successful status are verified before financial updates. Network verification runs before payment/order row locks.
- Settlement acquires the payment lock, then the order lock, then any referral lock. It commits the payment, order transition, seller payout, referral qualification, processed-event record, and outbox entry together. Failure rolls the transaction back so the same event can retry.
- Duplicate webhook IDs are checked against their payment and provider. Completed duplicates can be acknowledged without Redis or another provider request. Callback/webhook races serialize through PostgreSQL, and successful/reversed states cannot be downgraded by stale failures.
- A cancelled, rejected, refunded, or otherwise non-payable order is not revived by late money. The successful payment and `payment.review_required` audit record persist, a review notification is queued for active admins, and no new seller payout/referral is created. An operator must reconcile/refund the payment. No automatic refund or seller transfer is performed by this change.
- Successful legacy payments with no outbox entry are re-verified by reconciliation and completed where possible. Existing partial payouts/invoices are reused. Review legacy financial discrepancies before releasing actual funds; the application does not infer whether a real bank transfer occurred.
- The outbox records invoice/in-app notification work in the same transaction as settlement. Its consumer locks rows with `SKIP LOCKED`. Work and its completion marker commit together, so a crash or handler failure cannot leave duplicate committed invoice/notification effects on retry. Failed work uses capped retry backoff and stores only its error class, avoiding raw provider/customer details.
- The broker still must recover for Celery beat to schedule polling, but payment requests never need a successful broker publish. Committed outbox rows remain in PostgreSQL during a Redis/broker outage and are drained after workers resume.
- These guarantees cover local database effects. Future email, WhatsApp, payout-transfer, and PDF-storage delivery require provider idempotency keys and explicit external acknowledgement/reconciliation. Database transactions cannot make an external network side effect exactly once.

Services own transaction boundaries: `PaymentService` commits/rolls back its Session; do not call it with unrelated pending writes. Internal order/payout/referral/invoice methods accept `commit=False` to participate in the settlement/worker transaction. Outbox handlers must not commit, publish tasks, or call external providers.

## Monitoring and recovery

```sql
-- Pending/poison work and the age of the oldest eligible entry.
SELECT kind, count(*), min(created_at), max(attempts)
 FROM payment_outbox WHERE processed_at IS NULL GROUP BY kind;
SELECT id, kind, attempts, last_error, available_at
 FROM payment_outbox WHERE processed_at IS NULL ORDER BY available_at LIMIT 100;
-- Funds requiring manual review, including cancelled-order settlements.
SELECT resource_id AS payment_id, created_at, metadata_json
 FROM audit_logs WHERE action = 'payment.review_required' ORDER BY created_at DESC;
-- Legacy successful payments without a durable recovery record.
SELECT p.id, p.provider_reference FROM payments p
 WHERE p.status = 'successful'
   AND NOT EXISTS (SELECT 1 FROM payment_outbox o WHERE o.payment_id = p.id);
```

Alert on increasing outbox age, repeated handler failures, reconciliation errors, and new payment-review audit records. If the broker was unavailable, restore Redis, restart the payments worker and beat, and let the periodic poll drain the database. Diagnose the stored error class and worker logs before replaying poison work. Do not mark work processed simply to clear an alert. Retain completed outbox rows as payment deduplication/recovery markers; deleting them causes legacy reconciliation to treat the payment as unfinished. Any future archival design must preserve a durable tombstone. Once the cause is fixed, normal retries resume; an operator may bring `available_at` forward on a specific reviewed row if an immediate retry is needed.

The reconciler takes at most 200 references each run and rotates them by `last_reconciled_at`, so an old failing provider reference cannot indefinitely starve newer candidates. Each reference uses its own database session, and failures are rolled back before the next reference. Keep the configured provider stable for existing payments: switching providers requires per-payment provider routing, which is not implemented here and fails closed on a mismatch.

## Rollback

Stop writes and the beat/workers first. Prefer redeploying the prior application while retaining additive schema changes, after reviewing version compatibility; do not start the prior payment processor on new live funds without assessing its old partial-commit behavior. For a development rollback to the prior Alembic merge revision, resolve or drain pending work, take a backup, then run `alembic downgrade 2ab23f38e9c6`. Migration `0004` first refuses to discard catalog order snapshots or saved addresses. Migration `0003` refuses to drop pending work. Completed outbox history is removed by that schema downgrade, so retain a backup if it is needed for audit. Historical branch downgrades below the merge head are outside this change's supported rollback path.

## Tests and remaining work

CI creates the main service-test schema with Alembic and separately tests new databases and historical upgrades, record preservation, repeat upgrades, the new revision's downgrade/re-upgrade, duplicate-invoice rejection, JSON Boolean conversion, and pending-work downgrade rejection. Real PostgreSQL tests exercise settlement and commit failures, unprocessed legacy events, provider/broker outages, failed outbox work, concurrent callback/webhook settlement, competing workers, and late cancelled-order payments.

Model/migration drift still exists outside this payment path (including delivery ETA, payment consents, and KYC/KYB fields); those domains need separate reviewed schema repairs. The catalog checkout phase adds server-owned prices, persisted order lines, location/address schema repairs and recorded payment-session resumption; see [its contract and limits](catalog-checkout.md). Durable provider intent creation, multi-vendor payment grouping, inventory reservations, full refund/reversal sagas, supported international currency rules, PDF rendering, dependency vulnerabilities, and full browser/load/restore testing remain launch work. This PR does not make those flows production ready.
