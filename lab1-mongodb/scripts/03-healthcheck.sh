#!/usr/bin/env bash
set -Eeuo pipefail

mongo_uri="${MONGO_URI:-mongodb://127.0.0.1:27017/admin}"

if mongosh "$mongo_uri" --quiet --eval 'quit(db.adminCommand({ ping: 1 }).ok === 1 ? 0 : 1)' >/dev/null 2>&1; then
  echo "OK: MongoDB отвечает на ping"
else
  echo "ERROR: MongoDB недоступна" >&2
  exit 1
fi

