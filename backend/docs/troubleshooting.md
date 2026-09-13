# Troubleshooting

## `alembic upgrade head` fails with "type geography does not exist"

The PostGIS extension migration (`0001_enable_postgis_extension.py`) must
run first. If you created the database manually without running
migrations in order, run:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

then re-run `alembic upgrade head`.

## `psycopg.OperationalError: connection refused`

Postgres isn't reachable at `DATABASE_URL`. If running via Docker Compose,
confirm the `postgres` service is healthy: `docker compose ps`. If running
the API outside Docker against a Dockerized Postgres, make sure
`DATABASE_URL` points at `localhost:5432`, not the internal service name
`postgres`.

## Webhook returns 402/PaymentError "signature verification failed"

- Confirm `PAYMENT_WEBHOOK_SECRET` matches the value configured in your
  Paystack/Flutterwave dashboard for this specific webhook endpoint.
- Confirm your reverse proxy (Nginx) isn't mutating the request body
  before it reaches FastAPI — signature verification requires the exact
  raw bytes the provider signed.

## `ForbiddenError: Only the customer who placed this order can mark it as received`

This is intentional, not a bug — see
[orders.md](./orders.md#mark-as-received-rule). Only `order.buyer_user_id`
may call `/received`, enforced independently of route-level RBAC.

## Celery tasks aren't running

Confirm a worker is actually running (`make worker` / the `worker` service
in `docker-compose.yml`) and pointed at the same Redis instance as the API
(`CELERY_BROKER_URL`). `celery -A app.workers.celery_app inspect active`
shows currently executing tasks.

## Tests fail with "relation does not exist"

Create the test database and ensure `TEST_DATABASE_URL` is set; see
[testing.md](./testing.md).
