# Deployment

See `../deployment/README.md` for the full guide (topology diagram,
first-time VPS setup, routine operations, scaling path). This file exists
for the documentation index; the deployment folder is the source of truth
since it also holds the actual scripts/configs.

Quick reference:

```bash
# Local development
cd backend
cp .env.example .env   # fill in secrets
docker compose up --build

# Production (on a VPS)
docker compose -f docker-compose.yml -f deployment/docker/docker-compose.prod.yml up -d --build
docker compose run --rm api alembic upgrade head
docker compose run --rm api python scripts/create_admin.py --email you@example.com --password '...'
```

No Terraform, AWS, Azure, or GCP-specific tooling is used anywhere in this
repository, per the project's architecture principles — the stack is
Docker Compose + Nginx + PostgreSQL/PostGIS + Redis, portable to any VPS.
