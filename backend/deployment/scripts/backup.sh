#!/usr/bin/env bash
# Dumps the PostgreSQL database to a timestamped, gzip-compressed file.
# Schedule via cron, e.g.: 0 2 * * * /path/to/backup.sh >> /var/log/fashionhub-backup.log 2>&1
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/fashionhub}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
FILENAME="fashionhub_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "==> Backing up database to ${BACKUP_DIR}/${FILENAME}"
docker compose exec -T postgres pg_dump -U fashionhub fashionhub | gzip > "${BACKUP_DIR}/${FILENAME}"

# Keep the last 14 daily backups; adjust retention to your compliance needs.
find "$BACKUP_DIR" -name "fashionhub_*.sql.gz" -mtime +14 -delete

echo "==> Backup complete"
