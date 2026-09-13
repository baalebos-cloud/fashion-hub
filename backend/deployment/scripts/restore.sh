#!/usr/bin/env bash
# Restores a PostgreSQL dump produced by backup.sh.
# Usage: ./restore.sh /var/backups/fashionhub/fashionhub_20260101_020000.sql.gz
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <path-to-backup.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"

echo "==> WARNING: this will overwrite the current database. Press Ctrl+C to abort."
sleep 5

echo "==> Restoring from ${BACKUP_FILE}"
gunzip -c "$BACKUP_FILE" | docker compose exec -T postgres psql -U fashionhub -d fashionhub

echo "==> Restore complete"
