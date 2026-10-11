#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LOAD_SECONDS="${LOAD_SECONDS:-120}"
export LOAD_BATCH_SIZE="${LOAD_BATCH_SIZE:-100}"

mongosh \
  --host 127.0.0.1 \
  --port 27017 \
  --username lab_admin \
  --authenticationDatabase admin \
  --password \
  --file "$script_dir/generate-load.js"

