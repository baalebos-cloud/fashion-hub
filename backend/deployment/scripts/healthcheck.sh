#!/usr/bin/env bash
# Simple external healthcheck for use in cron/uptime monitoring, hitting
# the readiness endpoint (checks DB + Redis, not just process liveness).
set -euo pipefail

APP_URL="${APP_URL:-http://localhost:8000}"

response=$(curl -s -o /dev/null -w "%{http_code}" "${APP_URL}/health/ready")

if [ "$response" -ne 200 ]; then
    echo "Healthcheck FAILED (HTTP ${response})"
    exit 1
fi

echo "Healthcheck OK"
