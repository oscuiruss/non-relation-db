#!/usr/bin/env bash
set -Eeuo pipefail

backup_path="${1:-}"
if [[ -z "$backup_path" || ! -d "$backup_path" ]]; then
  echo "Использование: $0 <каталог backup university>" >&2
  exit 2
fi

mongorestore \
  --host 127.0.0.1 \
  --port 27017 \
  --username restore_user \
  --authenticationDatabase admin \
  --gzip \
  --drop \
  --nsInclude='university.students' \
  "$backup_path"

echo "Collection university.students restored"

