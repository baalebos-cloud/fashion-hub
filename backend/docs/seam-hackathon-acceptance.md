# Seam AI Commerce | Hackathon acceptance matrix

This document separates working repository functionality, new work, and required
external validation. It is not evidence of successful live payment integration.

| Phase | Acceptance evidence | Status / gate |
|---|---|---|
| 1 Interswitch backend | PR #47 builds a POST form and verifies a requery response | Foundation only; still requires order-bound payment service and merchant sandbox verification |
| 2 Customer checkout | Customer can create order, submit hosted payment form, return, and see independently verified paid order | Not yet integrated; never present as complete |
| 3 AI shopping | Catalog-grounded, budget-filtered product recommendations with no invented inventory | Pure deterministic recommendation core in this PR; authenticated API/UI wiring and Vertex reliability pending |
| 4 Reliability & security | Bad reference/amount, duplicates, timeout, concurrent settlement cannot credit unpaid orders | Payment primitives tested; full orchestration and e2e tests pending |
| 5 Marketplace operations | Tailor, vendor and courier roles can complete an order with permissions enforced | Existing app routes; production end-to-end testing pending |
| 6 Analytics/audit | Admin can see verified checkout conversion, incidents and customer impact | Instrumentation and authorization review pending; do not use fabricated metrics |
| 7 Hackathon demo | Live/sandbox real order, traceable requery result, clear validation story, alternate recorded demo | Pending merchant configuration, organizers' approval and user validation |

## Demo walk-through with honest status

1. Select an existing, published catalog item with confirmed stock.
2. Use the new recommendation core to show budget-matched real products.
3. Let a buyer create an order with server-calculated price.
4. Submit Interswitch hosted checkout form **only when** the approved
   merchant and Pay Item ID are configured in the selected environment.
5. Treat the return from the checkout page as untrusted. Requery server-side.
6. Mark the order paid only after reference and exact amount reconciliation.
7. Show audit events and a negative test (mismatched amount remains unpaid).
8. Capture validation quotes and numbers only from consenting real merchants.

## Five-person ownership plan

- **Payments/backend engineer:** scoped provider integration, order ownership,
  verification, idempotency and reconciliation.
- **Frontend engineer:** customer selection, hosted checkout POST, result pages,
  accessible pending/failed states.
- **AI engineer:** catalog grounding, recommendation ranking, Vertex fallback
  and evaluation.
- **QA/security engineer:** adversarial scenarios, CI, permissions, audit trails,
  concurrency and sandbox test evidence.
- **Product/design/validation lead:** merchant interviews, pitch, economic
  assumptions, launch checklist and organizer eligibility confirmation.

## Release rules

Keep the application-wide `PAYMENTS_ENABLED` flag disabled in production
until approved merchant configuration, server-side settlement and regression
checks are complete. Do not switch the default provider away from Paystack as
part of the hackathon. Require reviewed PRs and successful CI; do not merge
unverified changes. Avoid deploying preview frontend against a production
backend for mutation testing. AI recommendations never authorize payment.
