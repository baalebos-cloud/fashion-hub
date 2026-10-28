# Seam staging acceptance and production-release gate

## Observed environment (2026-10-28)
- Railway project: job-hunter-saas, environment: fashion-hub-staging.
- Fashion Hub backend, worker, and beat belong to baalebos-cloud/fashion-hub.
- Staging readiness API returned database=true and redis=true.
- Connector exposes the **names** of DATABASE_URL and REDIS_URL, not their values.
  These results do not establish separation from production datasets or queues.
- The staging environment also contains unrelated services and volumes. Do not
  alter those services as part of the Seam workstream.

## Required evidence before a real sandbox checkout
1. Confirm staging PostGIS and Redis references resolve to isolated test resources,
   using Railway's service reference UI; do not disclose connection strings.
2. Confirm the staging APP_ENV resolves to staging, sandbox flag to true, and
   APP_URL to the staging HTTPS backend, not the production backend.
3. Confirm CORS and frontend preview point exclusively at staging.
4. Use a dedicated test customer and a newly created test-only customer order.
5. Submit a provider-issued test payment only. Confirm provider reference and
   exact NGN minor units on Interswitch's **server-side requery**.
6. Repeat verification; ensure only one ledger payment and one settlement outbox.
7. Requery invalid/missing transactions; ensure no paid order is created.
8. Inspect test order timeline, payment audit records, and dashboard metrics.

## No-go conditions
- Unclear staging/prod database isolation or queue isolation.
- Staging credentials configured but unverifiable transaction ownership.
- Missing or incorrect Interswitch reference or amount.
- Failed backend/frontend/security CI.
- Live merchant credentials used for a test; production payment flag enabled.
- Automation that changes production without separate explicit approval.

## Phase status
- 1 / 3: Existing payment architecture and mocked regressions. End-to-end
  sandbox transaction not certified.
- 2: Infrastructure present, isolation still requires confirmation.
- 4: Grounded recommendation module exists; Vertex AI provider recovery pending.
- 5: Existing customer/professional/vendor routes require staged E2E evidence.
- 6: Admin verified-payment aggregation exists; audit and permissions need E2E.
- 7: Demonstration and business validation pending real merchant evidence.
- 8: Readiness evaluation only. No production payments or deployment approved.
