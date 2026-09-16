#!/usr/bin/env bash
# Dumps the whole database (including the users table, where only
# bcrypt password HASHES are stored -- never plaintext) to a timestamped
# file, and deletes local backups older than 14 days.
#
# Run this from cron every few hours, e.g.:
#   0 */6 * * *  /path/to/scripts/backup_db.sh >> /var/log/grandreserve_backup.log 2>&1
#
# For real production use, also copy BACKUP_DIR to off-site storage
# (S3, Backblaze B2, etc.) right after it's created.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

# DATABASE_URL_SYNC must be set (see .env.example), e.g.:
#   postgresql://booking_user:booking_pass@db:5432/booking_db
pg_dump "$DATABASE_URL_SYNC" --format=custom --file="$BACKUP_DIR/booking_db_$TIMESTAMP.dump"

echo "Backup written to $BACKUP_DIR/booking_db_$TIMESTAMP.dump"

find "$BACKUP_DIR" -name "booking_db_*.dump" -mtime "+$RETENTION_DAYS" -delete

echo "Removed backups older than $RETENTION_DAYS days."
