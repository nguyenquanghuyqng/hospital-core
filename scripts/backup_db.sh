#!/usr/bin/env bash
set -Eeuo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"

: "${PGDATABASE:?Set PGDATABASE before running backup}"
: "${PGUSER:?Set PGUSER before running backup}"

DATA_FILE="$BACKUP_DIR/${PGDATABASE}_${TIMESTAMP}.dump"
GLOBALS_FILE="$BACKUP_DIR/globals_${TIMESTAMP}.sql"

pg_dump --format=custom --file="$DATA_FILE" "$PGDATABASE"
pg_dumpall --globals-only --file="$GLOBALS_FILE"
shasum -a 256 "$DATA_FILE" "$GLOBALS_FILE" > "$DATA_FILE.sha256"

find "$BACKUP_DIR" -type f -mtime "+$RETENTION_DAYS" -delete
printf 'Backup complete:\n  %s\n  %s\n  %s\n' "$DATA_FILE" "$GLOBALS_FILE" "$DATA_FILE.sha256"
