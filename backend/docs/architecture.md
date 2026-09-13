# System Architecture

## Style: modular monolith

Fashion Hub is built as a single deployable FastAPI application with strict
internal module boundaries, not microservices. This is a deliberate choice
for the current stage:

- One team can reason about and deploy the whole system.
- Transactions that span "modules" (e.g. checkout touching cart, inventory,
  and orders) can use a single database transaction instead of distributed
  transactions/sagas.
- Extraction to a separate service later is cheap *because* business logic
  already lives behind service interfaces (see below), not inline in route
  handlers.

## Layering

```
API/Routes  (app/api/v1/*.py)
    -> validates input via Pydantic schemas (app/schemas/*.py)
    -> calls exactly one Service
Services    (app/services/*.py)
    -> business rules, state machines, authorization decisions
    -> calls Repositories for persistence, Integrations for external calls
Repositories (app/repositories/*.py)
    -> raw SQLAlchemy queries, no business logic
Integrations (app/integrations/*/*.py)
    -> Payment/Map/Delivery/KYC/AI/Storage provider abstractions
Database    (PostgreSQL + PostGIS, via app/models/*.py)
```

Route handlers are intentionally thin: they authenticate, authorize at the
role level, call one service method, and return its result. Every rule
that isn't "is this JSON shaped correctly" or "is this role allowed to hit
this route at all" lives in a service.

## Why provider abstractions

Payments, maps, delivery, KYC, notifications, storage, and AI are all
isolated behind an interface in `app/integrations/`. Concretely:

```
PaymentProvider (ABC)
├── PaystackProvider
└── FlutterwaveProvider
```

Services call `get_payment_provider()` (a factory reading
`settings.PAYMENT_PROVIDER`) and never import a concrete provider class.
Swapping Paystack for Flutterwave, or adding a third provider, is a change
in `app/integrations/payments/` plus one environment variable -- it never
touches `order_service.py`, `checkout_service.py`, or any route.

## Request flow example: placing a customer order

1. `POST /api/v1/orders` hits `app/api/v1/orders.py::create_order`.
2. Route requires role `customer` (`require_roles(Role.CUSTOMER)`).
3. Route calls `OrderService.create_customer_order(...)`.
4. Service checks `idempotency_key` for duplicate-submission protection,
   computes totals, and persists a `PENDING` order.
5. Response returns the order; the customer proceeds to
   `POST /api/v1/payments` (initialize) and is redirected to the provider.
6. The provider's webhook (`POST /api/v1/payments/webhooks/paystack`)
   verifies the signature, verifies the payment server-side, and calls
   `OrderService.mark_paid_from_webhook`, which is idempotent.
7. `PaymentService` enqueues `generate_invoice_for_order_task` (Celery).

## Background processing

Celery + Redis handle everything that shouldn't block a request: sending
emails/SMS/push, rendering invoice PDFs, broadcasting delivery requests to
nearby partners, reconciling pending payments, and detecting stale delivery
GPS tracking (`app/workers/celery_app.py` beat schedule).

## Deployment topology

See `../deployment/README.md` for the full VPS deployment guide. In short:
Nginx terminates TLS and reverse-proxies to FastAPI (Gunicorn + Uvicorn
workers); Celery worker/beat run as separate containers sharing the same
codebase and database.
