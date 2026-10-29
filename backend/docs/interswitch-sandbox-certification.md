# Interswitch sandbox certification runbook

This process does **not** authorize live payments or modify production payment flags.

## Readiness

Merge and deploy to **isolated staging**, then authenticate with an admin role and request:

`GET /api/v1/admin/interswitch-sandbox/readiness`

The response lists boolean checks only, never actual merchant identifiers.
All checks must be `true`. Set `APP_ENV=staging`,
`INTERSWITCH_SANDBOX_ENABLED=true`, `INTERSWITCH_MERCHANT_CODE`,
`INTERSWITCH_PAY_ITEM_ID`, and a public HTTPS `APP_URL` in staging.

## End-to-end sandbox acceptance

1. Seed a synthetic buyer, a verified tailor with a published design, and a distinct verified material vendor with stock. No real customers or payment credentials.
2. Create a customer `customer_order` and a separate tailor-to-material-vendor `vendor_order` through ordinary checkout. Ensure stock reservation is still active.
3. Authenticate as the buyer and POST `/api/v1/interswitch/checkout` with each order UUID.
4. Confirm action URL is the sandbox host, `txn_ref` is `FH-FAS-` or `FH-MAT-`, amount is the server-supplied NGN amount in kobo, and form fields contain no API secrets.
5. POST the resulting form to the Interswitch sandbox hosted checkout. Complete using the provider's sanctioned test-card flow.
6. On return, sign in as the same buyer and call `GET /api/v1/interswitch/{reference}/verify`. **Never** mark paid based on the redirect itself. The backend performs a requery.
7. Verify `payments`, `payment_transactions`, order status, `ledger_entries` and `payment_outbox` in the staging DB. Net debits minus credits must equal zero.
8. Repeat verification for the same reference and ensure no duplicate ledger/outbox effects.
9. Negative test: payment with the wrong amount or reference must not settle, and an unrelated buyer must not verify the order.
10. Confirm that `POST /api/v1/interswitch/live/checkout` remains disabled in staging.

If sandbox rejects a checkout, verify merchant/pay-item assignment and current provider gateway documentation before changing the code.

The existing integration/unit tests use mocked provider replies; they do **not** certify provider-hosted end-to-end settlement.
