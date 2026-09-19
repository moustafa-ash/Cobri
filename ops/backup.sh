#!/usr/bin/env bash
set -euo pipefail
: "${COBRI_DATABASE_URL:?Set a disposable PostgreSQL database URL}"
: "${COBRI_BACKUP_FILE:?Set an explicit backup file path}"
[[ "$COBRI_DATABASE_URL" == postgres* ]] || { echo "PostgreSQL URL required" >&2; exit 2; }
DATABASE_URL="${COBRI_DATABASE_URL/+asyncpg/}"
pg_dump --format=custom --no-owner --file "$COBRI_BACKUP_FILE" "$DATABASE_URL"
pg_restore --list "$COBRI_BACKUP_FILE" >/dev/null
echo "Backup archive verified: $COBRI_BACKUP_FILE"
