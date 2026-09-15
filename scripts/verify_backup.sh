#!/usr/bin/env bash
set -Eeuo pipefail

BACKUP_FILE="${1:?Usage: verify_backup.sh /path/to/database.dump}"
: "${BACKUP_FILE:?Backup file is required}"

pg_restore --list "$BACKUP_FILE" >/dev/null
if [[ -f "$BACKUP_FILE.sha256" ]]; then
  shasum -a 256 --check "$BACKUP_FILE.sha256"
fi
printf 'Backup archive is readable: %s\n' "$BACKUP_FILE"
