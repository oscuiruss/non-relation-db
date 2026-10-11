#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
destination="$repo_root/backups/${timestamp}-university"
mkdir -p "$destination"

mongodump \
  --host 127.0.0.1 \
  --port 27017 \
  --username backup_user \
  --authenticationDatabase admin \
  --db university \
  --gzip \
  --out "$destination"

echo "Backup created: $destination"

