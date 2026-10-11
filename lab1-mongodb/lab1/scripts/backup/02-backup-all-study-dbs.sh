#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive="$repo_root/backups/${timestamp}-all-study-dbs.archive.gz"
mkdir -p "$(dirname "$archive")"

mongodump \
  --host 127.0.0.1 \
  --port 27017 \
  --username backup_user \
  --authenticationDatabase admin \
  --gzip \
  --archive="$archive" \
  --nsInclude='university.*' \
  --nsInclude='library.*'

echo "Backup created: $archive"

