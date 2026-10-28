# Seam AI Commerce: Interswitch hackathon implementation plan

## Scope and readiness
This branch introduces **only isolated, offline-tested payment primitives**. It does not
enable Interswitch for users and does not change Paystack, Flutterwave, payment
database records, live settings or the current PaymentProvider factory.

Hackathon proof of concept, not production launch. Confirm organizer eligibility
for reusing an existing codebase. Validate the team merchant code, Pay Item ID,
approved merchant environment, settlement arrangements and return domain.

## Target customer journey
Customer selects a published tailor design and provides measurements. Backend
validates catalog/order ownership, stock (where relevant), order pricing and
the currently enabled payment provider. Only the server computes the payable
amount. On explicitly approved Interswitch checkout, server creates and stores
a unique transaction reference, sends the checkout form fields to the UI,
and the browser **POSTs** them to Interswitch. On return, ignore all callback
status indicators and requery Interswitch from the backend. Match the stored
merchant reference, exact amount in kobo and success response code. Only then
may PaymentService atomically settle the corresponding order and audit event.

## Security gates before enabling
- Extend provider orchestration to support a browser POST form explicitly. Do
  **not** send POST-only checkout fields through the URL-returning provider
  interface; do not redirect with credentials or trust browser payment data.
- Add explicit Interswitch merchant configuration with server validation,
  separately scoped to sandbox; retain PAYMENTS_ENABLED=false for production.
- Generate unique unpredictable references, bind to an authorized buyer/order,
  and persist the expected merchant, amount, currency and provider.
- Whitelist exact callback origins. Never let clients set arbitrary destinations.
- Only backend requery counts. Enforce reference/amount/currency, payment
  ownership, idempotency, event auditing and replay/race handling.
- Reject wrong merchant, mismatched transaction, partial amount, missing
  expected fields, HTTP failures and duplicate settlement.
- No unauthenticated webhook path unless actual Interswitch signature mechanism
  is verified and independently tested; use secure requery instead.
- Never place merchant keys, provider responses containing PII, or bearer
  credentials in public client bundles or logs.
- Exercise successful, failed, pending, duplicate, race and timeout scenarios
  under mocked integration tests, then sandbox e2e tests. Obtain explicit
  approval before a controlled live-value demonstration.

## AI
Add catalog-grounded, role-scoped style/material recommendations with a
deterministic fallback when Vertex is unavailable. Never let a model invent
prices, approve KYB or mark payments successful. Keep API permissions separate
from the pending Google 403 issue.

## Demo and measurement
Show verified catalogue -> order price -> Interswitch sandbox checkout -> backend
requery -> paid order -> receipt, including a negative test where an incorrect
amount **does not** produce a paid order. Measure checkout completion, time to
find a tailor/material, and seller onboarding friction with real test users.
Do not present hypothetical economic uplift as measured impact.

References:
- https://docs.interswitchgroup.com/docs/web-checkout
- https://docs.interswitchgroup.com/docs/quickstart-accept-your-first-payment-in-5-minutes
