# Testing

## Strategy

- **Unit tests** (`tests/unit/`) — exercise services directly against a
  real (transactional, rolled-back-per-test) PostgreSQL connection, with
  external providers mocked (`unittest.mock.patch`). This is where the
  state-machine and idempotency edge cases are covered:
  `test_orders.py`, `test_payments.py`, `test_cart.py`, `test_reviews.py`.
- **Integration tests** (`tests/integration/`) — placeholders for
  end-to-end flows requiring live Postgres + Redis (skipped by default;
  remove the `pytest.mark.skip` once CI provisions those services, which
  the included GitHub Actions workflow already does).
- **API tests** (`tests/api/`) — exercise routes via FastAPI's
  `TestClient`. `test_order_api.py::test_all_required_order_routes_are_registered`
  is a regression guard that the exact required order endpoint surface
  stays registered.

## Why PostgreSQL for tests, not SQLite

Several models use PostgreSQL-specific types (`UUID`, `JSONB`, `ARRAY`,
PostGIS `Geography`) that SQLite can't represent faithfully. `tests/conftest.py`
connects to `TEST_DATABASE_URL` (defaults to a local `fashionhub_test` DB)
and wraps each test in a transaction that's rolled back afterward, so tests
don't need to share fixtures across runs and leave no residue.

## Running the suite

```bash
# One-time: create the test database
createdb fashionhub_test  # or via docker compose exec postgres createdb ...

make test
# or directly:
pytest --cov=app --cov-report=term-missing
```

## What's covered vs. stubbed

Fully implemented and tested: signup/login, the customer order state
machine (including the mark-as-received rule and cross-tenant ownership
checks), idempotent payment webhook handling, cart stock checks, and the
review-after-received rule.

Explicitly stubbed with `NotImplementedError` (and documented as such in
their docstrings) pending further product/infra decisions: PDF rendering,
PostGIS nearest-neighbor queries, full-text search, and SMS/push sending.
Each stub's docstring states exactly what needs to be wired in.
