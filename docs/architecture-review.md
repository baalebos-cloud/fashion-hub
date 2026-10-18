# Architecture review and production scaling plan

Reviewed baseline: `1974dea3f0efb1fd87eb86bee4942bf4452f0dc3` on 2026-10-16.

## Assessment

The project is a modular application scaffold with some working marketplace services. Its existing stack is suitable for an initial production marketplace. The immediate constraint is incomplete and unsafe business flows, rather than a need for more infrastructure. No traffic target, country rollout, production database state, or operating budget has been confirmed; capacity numbers below are proposed acceptance targets, not measured guarantees.

The repository contains a React 18/TypeScript/Vite SPA using Axios and Zustand; a FastAPI API grouped by domain; SQLAlchemy repositories and PostgreSQL/PostGIS models; Redis and Celery workers; payment, identity, mapping, storage, and notification adapters; and Docker/Nginx deployment assets. Thirty-five API modules contain scaffold/placeholder declarations. Search, nearby dispatch, and invoice PDF rendering raise `NotImplementedError`. Several API and end-to-end tests are skipped or placeholders.

## Recommended architecture

Retain one API deployment and explicit domain boundaries while completing the marketplace. Each API replica should be stateless; PostgreSQL owns durable business state, Redis owns short-lived coordination, and workers handle retryable background work. Share provider interfaces and business services between request handlers and workers. Keep privileged operations under explicit role and resource authorization.

```mermaid
flowchart LR
    Browser[React application] --> Edge[CDN and TLS ingress]
    Edge --> Assets[Static assets]
    Edge --> API[Stateless FastAPI replicas]
    API --> DB[(PostgreSQL and PostGIS)]
    API --> Redis[(Redis)]
    API --> Providers[Payment and identity providers]
    DB --> Outbox[Transactional payment outbox]
    Outbox --> Workers[Celery workers]
    Redis --> Workers
    Workers --> Storage[Object storage]
    Workers --> Notifications[Email and notifications]
```

The payment outbox is implemented in the follow-up payment recovery change; see [the runbook](payment-recovery.md). The diagram remains a target for other domain events. Use the existing modules as bounded domains: identity/access; catalog/professional profiles; orders/checkout/inventory; payments/refunds/payouts; fulfillment; communications; verification; and administration/audit. Keep API handlers thin and let services own authorization, business rules, and transaction boundaries. Avoid splitting these into independent services until measured traffic or team ownership warrants it.

## Fixes proposed in this PR

| Finding | Change |
| --- | --- |
| Password backend versions break ordinary hashing; raw bcrypt truncates long passwords | Pin the compatible bcrypt backend, prehash new passwords with `bcrypt_sha256`, and retain legacy bcrypt verification |
| Public signup accepts `admin` through an unrestricted role string and enum check | Restrict the request schema and service allowlist to public roles |
| Wildcard credentialed CORS; weak production settings accepted | Use configured origins and reject unsafe staging/production settings |
| Limiter configured without enforcement middleware; authentication limits only documented | Install shared limiter middleware and apply authentication endpoint limits; require Redis storage in production |
| Database module references an undefined `Generator`, lacks imported health/session helpers, and rewrites specific database URLs | Restore explicit sessions, rollback and health helpers, remove host-specific URL rewriting, bound connection waits |
| Readiness returns HTTP 200 when dependencies fail | Return 503 for failed readiness; keep liveness independent |
| Payment endpoints lack buyer ownership checks and settlements lack identity checks | Validate buyer ownership, reference, exact amount, and currency before accepting provider results |
| Missing webhook secrets can validate as empty strings; Paystack signs with the wrong setting | Fail closed and use the Paystack account secret; validate bounded payloads after signature verification |
| Customer cancellation and delivery transitions lack complete resource ownership checks | Check the buyer and assigned courier; reject client-driven payment transitions |
| Refresh 401 re-enters its own Axios interceptor and waits forever | Use an isolated refresh transport and one refresh promise per API client |
| CI workflows live below `backend/.github`, where GitHub does not run them | Add a repository-root workflow with backend and frontend checks |
| Container lacks a real health check and runs as root | Run as a non-root user, use an explicit health check, and keep ports consistent |

Production configuration now requires `APP_ENV=production`, `DEBUG=false`, `DATABASE_ECHO=false`, a random secret of at least 32 characters, explicit HTTPS origins in a JSON array, and Redis-backed `RATE_LIMIT_STORAGE_URI`. Example values are not production credentials. Only trust forwarding headers from the deployment's known ingress; otherwise clients can spoof IP-based rate-limit keys. Configure aggregate connection limits as `replicas × workers × (pool_size + max_overflow)` within the database's connection budget, preferably with a pooler.

## Remaining launch blockers

These are not fixed by this PR and must remain visible during review.

1. **Payment transaction durability (addressed for local settlement in the follow-up PR; external effects remain):** The follow-up change commits payment/order/payout/referral/event/outbox records atomically and retries database invoice/notification work. It tests duplicate and concurrent deliveries and rollback/recovery. See [the recovery runbook](payment-recovery.md) for its scope. External payout transfers, refund/reversal sagas, PDF/storage and external notifications still need their own idempotency and reconciliation before live-money launch.
2. **Authoritative pricing and order items (published catalog path addressed):** catalog checkout resolves published designs server-side, validates ownership/measurement requirements, and commits Decimal prices, items and private fulfillment snapshots atomically. Idempotency keys are bound to canonical request intent, and legacy untrusted customer orders cannot initialize new payments. Address/measurement creation, verified callback UI and authorized invoice reads are connected. See [the checkout contract](catalog-checkout.md). Custom quotes, shipping/tax pricing, order expiry, fulfillment snapshot reads and durable provider initialization intents remain.
3. **Migration history (ordering repair and upgrade coverage added):** the follow-up declares `0002`'s dependency on initial table creation without changing revision IDs or historical SQL. Fresh and supported historical upgrades are tested, and the main service suite now uses migrations. Existing unstamped/create_all databases and inconsistent manually edited schemas still require an explicit adoption plan; do not stamp or rewrite data blindly. See the recovery runbook before upgrading.
4. **Checkout and inventory:** multi-vendor payment grouping is described but not implemented as a complete durable flow; cart/vendor identifiers contain placeholders, stock reservation expiry is absent, and snapshot prices can become stale. Lock cart and inventory rows, aggregate quantities, validate ownership, add reservation expiry/release and idempotency, and test two buyers competing for the last item.
5. **Authentication lifecycle:** add one-time password reset tokens, atomic refresh rotation/reuse detection, session expiry/uniqueness constraints, verified-account policies, and MFA for privileged accounts. Browser tokens remain JavaScript-accessible; evaluate an HttpOnly cookie/BFF session architecture with explicit CSRF protection before a wider release.
6. **Incomplete user journeys:** complete catalog discovery, professional profile provisioning, fulfillment snapshot reads, address/measurement editing, vendor checkout, tracking, delivery assignment, reviews, invoice PDF/storage, refunds, dispute handling, and administration. Replace successful-looking placeholders with implemented behavior or explicit unavailable states.
7. **Data integrity and privacy:** most UUID associations do not have foreign keys. Add constraints and indexes through reviewed migrations after checking existing data. Separate public profile/portfolio assets from private KYC documents; enforce signed access, encryption, retention/deletion, audit coverage, and least privilege. Do not log sensitive identity payloads or payment secrets.
8. **Test coverage:** replace skipped API and end-to-end placeholders with complete role-based flows. A test asserting `NotImplementedError` proves an unfinished contract, not readiness. Add concurrency and failure-injection tests using real PostGIS/Redis and sandbox payment accounts.
9. **Dependency and platform security (dependency remediation added):** the security phase resolves the nine frontend findings, replaces vulnerable JWT dependencies, upgrades affected Python packages, removes the unused PDF engine, adds Argon2id with legacy-hash migration, and verifies hashed locks with ongoing audits/Dependabot. See [the security rollout](dependency-security.md) for the snapshot and compatibility limits. Image scanning, SBOMs, runtime/development image separation and the remaining authentication lifecycle work are still open.

## Delivery stages and acceptance gates

| Stage | Deliverables | Acceptance gate |
| --- | --- | --- |
| Foundation, this PR | Targeted security/operational fixes, regression tests, executable CI, this review | Review diff; run full CI; preserve explicit open launch blockers |
| Transactional marketplace | Server-owned prices, persisted items, safe migrations, durable settlement/outbox, inventory reservations, complete invoices/refunds | Signup → discover → quote/order → pay → fulfill → receive → invoice works; wrong-user requests fail; repeated callbacks cannot create duplicate financial effects |
| Regional production | Managed PostGIS, managed Redis, private object storage, worker queues, staging, backups, monitoring, privileged MFA | Restore rehearsal passes; alerts reach an owner; agreed SLOs and incident/rollback runbooks tested |
| International expansion | Country capability registry, local payment/shipping/tax integrations, language/currency/unit handling, privacy processes | Each enabled country passes its own payment, tax, delivery, support, and regulatory readiness review |
| Measured scale | CDN, query/index tuning, connection pooling, independent workers, then replicas/caches/search where justified | Load tests meet SLOs without overselling, double charging, data leakage, or exceeding cost/connection budgets |

Start in one primary write region with managed failover and CDN delivery worldwide. Do not use multi-region writes for orders/payments without a proven consistency model. Route country-specific payment, delivery, verification, tax, and currency capabilities through explicit configuration; display unsupported markets honestly. Do not infer that accepting a currency provides shipping, tax, consumer support, or regulatory coverage in that country.

For internationalization, centralize translations and locale selection; use `Intl` formatting and explicit IANA timezones; store money as exact decimal values with currency and currency-specific minor-unit rules; normalize phone numbers to E.164; model structured addresses by country; keep measurement units explicit; support keyboard, screen-reader, contrast, and mobile flows to WCAG 2.2 AA. Provider adapters currently have NGN/two-decimal assumptions that must be reviewed before enabling additional currencies.

## Operations and scaling verification

Proposed initial targets to agree with the product owner: 99.9% monthly availability for the ordering API; p95 below 500 ms for ordinary reads and 1 s for ordinary writes excluding external provider latency; zero duplicate settlements and no overselling; database restore point within 15 minutes and recovery within 60 minutes. Validate and revise these against business cost, traffic, and provider constraints.

Measure API latency/errors/throughput by route, database pool utilization and slow queries, Redis errors, worker queue depth/oldest job age/retries, webhook lag, unmatched settlements, inventory shortfalls, and payout reconciliation. Propagate request/event identifiers into structured logs and tracing. Exclude secrets and private documents. Define payment-error and queue-backlog alerts with an owner and a runbook.

Load-test catalog reads, concurrent checkout, webhook bursts, and queue recovery with a production-like dataset. Add composite indexes based on actual query plans, use keyset pagination for large feeds, cache public catalog reads with bounded TTLs, and invalidate after writes. Add search infrastructure only when Postgres full-text/PostGIS searches no longer meet measured requirements. Keep private/order/payment responses out of shared CDN caches.

Run migrations once as a reviewed release step, not independently in every API replica. Deploy to staging, smoke-test all personas, test backward compatibility with the prior application image, then release gradually with rollback instructions. Preserve financial/audit records during rollback. Back up database and object storage independently and test restoration regularly.

## Verification record

Local environment: Python 3.12 and Node 24 are installed, but the workspace network proxy cannot reach GitHub/package registries. Source was obtained and the review branch published through the authenticated GitHub connection. Seven dependency-light settlement/configuration tests pass locally, Python compilation passes, and static local-import and whitespace checks pass.

GitHub Actions run [38875824126](https://github.com/baalebos-cloud/fashion-hub/actions/runs/38875824126) verified backend startup, the foundation tests, PostgreSQL/PostGIS and Redis service tests, frontend lint, 11 frontend tests, and the production TypeScript/Vite build. Nine existing backend tests remain skipped because they are placeholders; passing CI does not establish complete user-journey coverage. Later runs on the PR also cover the added rate-limit and payment-ownership regressions. Review the latest CI results before merging. The frontend install reports nine dependency vulnerabilities (seven high and two moderate); dependency remediation remains a release blocker.

No Docker build, full browser end-to-end verification, production deployment, restore rehearsal, or load test has been performed.


### Catalog checkout verification

The catalog checkout phase was verified in [Actions run 38900084684](https://github.com/baalebos-cloud/fashion-hub/actions/runs/38900084684): 89 backend tests passed, nine existing placeholders remained skipped, and 17 frontend tests plus lint/TypeScript/Vite checks passed. Coverage includes real PostGIS migrations, lost-response recovery, concurrent checkout/payment initialization, price/ownership rejection, and the HTTP order-to-invoice flow with a mocked payment provider. The [rollout guide](catalog-checkout.md) records the required migration and remaining live-order gates. No project/live database or provider account was used for these tests.
