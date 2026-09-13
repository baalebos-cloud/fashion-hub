# Deployment

This directory documents the deployment layer independently from
application code, as required by the project's architecture principles:
the platform stays provider-agnostic and suitable for any VPS/self-managed
infrastructure (Contabo, Hetzner, DigitalOcean, or similar) -- no
Terraform, AWS, Azure, or GCP-specific tooling is used.

## Runtime topology

```
Internet
   |
   v
Nginx (TLS termination, reverse proxy)
   |
   +--> FastAPI (api service, Gunicorn + Uvicorn workers)
   +--> Celery worker (background jobs)
   +--> Celery beat (scheduled jobs)
   |
   +--> PostgreSQL + PostGIS
   +--> Redis
   +--> External providers (payments, maps, delivery, KYC, AI, storage)
```

## First-time setup on a fresh VPS

1. Install Docker + Docker Compose plugin.
2. Clone the repository.
3. Copy `backend/.env.example` to `backend/.env` and fill in real secrets.
4. From `backend/`: `docker compose -f docker-compose.yml -f deployment/docker/docker-compose.prod.yml up -d --build`
5. Run `docker compose run --rm api alembic upgrade head` to create the schema.
6. Run `docker compose run --rm api python scripts/create_admin.py --email you@example.com --password '...'`
7. Point DNS at the server and configure TLS (e.g. certbot) in `deployment/nginx/conf.d/app.conf`.

## Routine operations

- **Deploy an update:** `deployment/scripts/deploy.sh`
- **Backup the database:** `deployment/scripts/backup.sh` (schedule via cron)
- **Restore a backup:** `deployment/scripts/restore.sh <file>`
- **External healthcheck:** `deployment/scripts/healthcheck.sh`

## Scaling path

The application starts as a modular monolith. When a specific module
(e.g. AI, delivery tracking) needs independent scaling, it can be split out
because business logic already lives behind service interfaces rather than
inline in route handlers -- extraction becomes a matter of moving a service
+ its routes into a new deployable, not a rewrite.
