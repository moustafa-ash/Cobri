#!/usr/bin/env bash
set -euo pipefail
: "${COBRI_RESTORE_DATABASE_URL:?Set an explicit disposable target database URL}"
: "${COBRI_BACKUP_FILE:?Set a verified backup archive}"
[[ "$COBRI_RESTORE_DATABASE_URL" == postgres* ]] || { echo "PostgreSQL target URL required" >&2; exit 2; }
EXPECTED_CONFIRMATION="RESTORE:${COBRI_RESTORE_DATABASE_URL}"
[[ "${COBRI_RESTORE_CONFIRMATION:-}" == "$EXPECTED_CONFIRMATION" ]] || {
  echo "Refusing restore; COBRI_RESTORE_CONFIRMATION must exactly match RESTORE:<target URL>" >&2
  exit 2
}
pg_restore --list "$COBRI_BACKUP_FILE" >/dev/null
DATABASE_URL="${COBRI_RESTORE_DATABASE_URL/+asyncpg/}"
pg_restore --clean --if-exists --no-owner --dbname "$DATABASE_URL" "$COBRI_BACKUP_FILE"
