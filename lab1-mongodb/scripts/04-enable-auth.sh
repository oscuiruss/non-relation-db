#!/usr/bin/env bash
set -Eeuo pipefail

config=/etc/mongod.conf
backup="/etc/mongod.conf.before-auth.$(date -u +%Y%m%dT%H%M%SZ)"

cp "$config" "$backup"

if grep -Eq '^security:[[:space:]]*$' "$config"; then
  if ! grep -Eq '^[[:space:]]+authorization:[[:space:]]+enabled[[:space:]]*$' "$config"; then
    sed -i '/^security:[[:space:]]*$/a\  authorization: enabled' "$config"
  fi
elif grep -Eq '^#security:[[:space:]]*$' "$config"; then
  sed -i '/^#security:[[:space:]]*$/c\security:\n  authorization: enabled' "$config"
else
  printf '\nsecurity:\n  authorization: enabled\n' >>"$config"
fi

systemctl restart mongod
systemctl is-active --quiet mongod

echo "Авторизация включена. Backup конфигурации: $backup"

