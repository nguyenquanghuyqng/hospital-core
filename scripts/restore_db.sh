#!/usr/bin/env bash
set -Eeuo pipefail

BACKUP_FILE="${1:?Usage: restore_db.sh /path/to/database.dump}"
: "${PGDATABASE:?Set PGDATABASE before running restore}"
: "${PGUSER:?Set PGUSER before running restore}"

if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "This will replace database '$PGDATABASE'. Set CONFIRM_RESTORE=YES to continue." >&2
  exit 2
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

pg_restore --list "$BACKUP_FILE" >/dev/null
psql -v ON_ERROR_STOP=1 -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$PGDATABASE' AND pid <> pg_backend_pid();" >/dev/null || true
pg_restore --clean --if-exists --exit-on-error --dbname="$PGDATABASE" "$BACKUP_FILE"

if [[ -n "${GLOBALS_FILE:-}" && -f "$GLOBALS_FILE" ]]; then
  psql -v ON_ERROR_STOP=1 -d postgres -f "$GLOBALS_FILE" >/dev/null
fi

if command -v alembic >/dev/null 2>&1; then
  alembic upgrade head
fi

psql -v ON_ERROR_STOP=1 -d "$PGDATABASE" -c 'SELECT 1;' >/dev/null
printf 'Restore complete for %s from %s\n' "$PGDATABASE" "$BACKUP_FILE"
