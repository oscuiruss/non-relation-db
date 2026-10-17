#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="$repo_root/backups/${timestamp}-all-study-dbs"
mkdir -p "$backup_dir"

for database in university library; do
  mongodump \
    --host 127.0.0.1 \
    --port 27017 \
    --username backup_user \
    --authenticationDatabase admin \
    --db "$database" \
    --gzip \
    --out "$backup_dir"
done

echo "Backup created: $backup_dir"
