# Fashion Hub — Backend

A modular-monolith FastAPI backend for a fashion marketplace connecting
**customers**, **tailors/fashion designers**, **material vendors**, and
**delivery partners**.

```
Customer  <->  Tailor/Designer  <->  Vendor
    \___________________________________/
                   |
            Delivery Partner
```

## Stack

Python · FastAPI · PostgreSQL + PostGIS · Redis · SQLAlchemy · Alembic ·
Pydantic · Celery · Docker Compose · Nginx — no cloud-specific/IaC tooling;
deploys to any VPS (Contabo, Hetzner, DigitalOcean, or similar).

## Quick start (local development)

```bash
cp .env.example .env        # fill in secrets (or leave defaults for local dev)
docker compose up --build   # postgres, redis, api, worker, beat, nginx

# in another shell, once the stack is up:
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_database.py
docker compose exec api python scripts/create_test_users.py
```

API docs: http://localhost:8000/docs
Health check: http://localhost:8000/health/ready

## Project layout

```
app/
  core/            settings, database, security, RBAC, exceptions, logging
  api/v1/          route modules (thin: RBAC -> one service call -> return)
  models/          SQLAlchemy ORM models
  schemas/         Pydantic request/response models
  repositories/    raw query layer, no business logic
  services/        business rules, state machines, authorization
  integrations/    provider abstractions (payments, maps, delivery, KYC, AI, storage, notifications)
  workers/         Celery task definitions
  events/          lightweight in-process pub/sub for cross-cutting side effects
  utils/           pure helper functions
  templates/       email + invoice HTML templates
migrations/        Alembic migrations
tests/             unit / integration / api tests
scripts/           seed_database.py, create_admin.py, create_test_users.py
docs/              full documentation set (see docs/README.md)
deployment/        VPS deployment: docker compose overrides, nginx, scripts
```

## What's fully implemented vs. scaffolded

**Fully implemented, production-quality reference modules:**
- Authentication (`auth_service.py`, `app/api/v1/auth.py`)
- Order lifecycle state machine, including the mark-as-received rule and
  cross-tenant ownership checks (`order_service.py`, `app/api/v1/orders.py`)
- Idempotent, signature-verified payment webhook processing
  (`payment_service.py`, `app/api/v1/payment_webhooks.py`)
- Multi-vendor cart + atomic, oversell-safe checkout
  (`cart_service.py`, `checkout_service.py`)
- Payment/Maps/Delivery/KYC provider abstractions
  (`app/integrations/`)

**Documented scaffolds** (module docstrings state exactly what to wire in):
all other route modules, PDF invoice rendering, PostGIS nearest-neighbor
queries, full-text search, SMS/push sending.

See `docs/README.md` for the full documentation index, and
`docs/orders.md` in particular for the exact required order-endpoint
surface this backend implements.

## Required order endpoints (implemented exactly)

```
GET  /api/v1/orders
GET  /api/v1/orders/{order_id}
POST /api/v1/orders/{order_id}/accept
POST /api/v1/orders/{order_id}/start-production
POST /api/v1/orders/{order_id}/ready
POST /api/v1/orders/{order_id}/ship
GET  /api/v1/orders/{order_id}/tracking
POST /api/v1/orders/{order_id}/received
GET  /api/v1/orders/{order_id}/timeline
POST /api/v1/orders/{order_id}/review
```

## Testing

```bash
createdb fashionhub_test
make test
```

See `docs/testing.md`.

## License

Proprietary — internal project scaffold.
