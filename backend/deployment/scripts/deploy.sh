#!/usr/bin/env bash
# Zero-frills deploy script for a self-managed VPS (Contabo/Hetzner/
# DigitalOcean/etc.). Pulls latest code, rebuilds images, runs migrations,
# and restarts services with minimal downtime via `docker compose up -d`.
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "==> Pulling latest code"
git pull origin main

echo "==> Building images"
docker compose -f docker-compose.yml -f deployment/docker/docker-compose.prod.yml build

echo "==> Running database migrations"
docker compose run --rm api alembic upgrade head

echo "==> Restarting services"
docker compose -f docker-compose.yml -f deployment/docker/docker-compose.prod.yml up -d

echo "==> Deployment complete"
