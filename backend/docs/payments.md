# Payments

## Provider abstraction

```
PaymentProvider (ABC)          app/integrations/payments/base.py
├── PaystackProvider           app/integrations/payments/paystack.py
└── FlutterwaveProvider        app/integrations/payments/flutterwave.py
```

`get_payment_provider()` resolves the active provider from
`settings.PAYMENT_PROVIDER`. Services never import a concrete class.

## Golden rule: never trust the client

The order is marked `PAID` **only** after one of:

1. A signature-verified webhook (`process_webhook`), or
2. A server-to-server verification call (`verify_and_confirm`, used by the
   payment-callback redirect endpoint as a belt-and-suspenders check for
   the "webhook arrives late" case).

The frontend's "payment succeeded" redirect is never itself sufficient.

## Idempotent webhook processing

Two layers of de-duplication (see `payment_service.py::process_webhook`):

1. **Redis `SETNX` lock** keyed by `provider_event_id`, short-circuits
   duplicates arriving within the TTL window.
2. **Unique DB constraint** on `payment_transactions.provider_event_id` —
   the durable backstop if the Redis lock is lost/expired. A duplicate
   insert raises `IntegrityError`, caught and treated as a no-op.

This directly covers both "webhook arrives late" and "webhook arrives
twice" from the edge-case list.

## Reconciliation job

`app/workers/payment_tasks.py::reconcile_pending_payments_task` runs every
5 minutes (Celery beat) and re-verifies any payment stuck in
`initialized`/`pending`, so a webhook that never arrives at all doesn't
leave an order stuck forever.

## Refunds

`RefundService.request_refund` → `approve_refund` (admin only) →
`process_refund_task` (Celery, retries on transient provider failure) →
`PaymentProvider.initiate_refund`.
