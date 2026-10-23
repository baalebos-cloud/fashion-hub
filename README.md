# Fashion Hub

A marketplace connecting customers, tailors/designers, material vendors, and delivery partners. The application uses React/TypeScript, FastAPI, PostgreSQL/PostGIS, Redis, and Celery.

This repository contains working features alongside scaffolded modules. Read the [architecture review and scaling plan](docs/architecture-review.md) before planning a production launch. The hardening changes improve specific security and operational boundaries; they do not make every marketplace flow production ready.

## Development

- Backend instructions: [backend/README.md](backend/README.md).
- Frontend instructions: [frontend/README.md](frontend/README.md).
- Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env.local`. Keep credentials out of Git.
- Dependency maintenance and credential compatibility: [security rollout](docs/dependency-security.md).
- API port: `8005`; Vite port: `5173`. The Vite development proxy forwards `/api` to the API.
- Read the [migration and payment recovery runbook](docs/payment-recovery.md) before upgrading. The migration ordering is repaired and tested, and this checkout requires migration `0005`.
- Read the [catalog checkout contract and rollout](docs/catalog-checkout.md) for the breaking order API change, retry behavior and remaining launch blockers.

## Checks

```sh
cd backend
python -m pip install --require-hashes -r requirements.txt
python -m unittest discover -s tests/foundation -v
pytest tests --cov=app --cov-report=term-missing
```

The complete backend suite needs a dedicated PostgreSQL/PostGIS test database and Redis. Set `TEST_DATABASE_URL`, `DATABASE_URL`, and `REDIS_URL`; never point tests at production.

```sh
cd frontend
npm ci
npm run lint
npm test
npm run build
```

GitHub Actions runs these checks from the repository root workflow. CI has no deployment or merge step. Deployment and migration changes must be reviewed separately.
