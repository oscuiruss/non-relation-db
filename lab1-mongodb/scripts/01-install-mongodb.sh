#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$(. /etc/os-release; printf '%s' "$VERSION_CODENAME")" != "noble" ]]; then
  echo "Этот скрипт рассчитан на Ubuntu 24.04 (noble)." >&2
  exit 1
fi

architecture="$(dpkg --print-architecture)"
if [[ "$architecture" != "arm64" && "$architecture" != "amd64" ]]; then
  echo "Неподдерживаемая архитектура: $architecture" >&2
  exit 1
fi

apt-get update
apt-get install -y curl gnupg ca-certificates

install -d -m 0755 /usr/share/keyrings
curl -fsSL https://pgp.mongodb.com/server-8.0.asc \
  | gpg --dearmor \
  | tee /usr/share/keyrings/mongodb-server-8.0.gpg >/dev/null
chmod 0644 /usr/share/keyrings/mongodb-server-8.0.gpg

echo "deb [arch=${architecture} signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/8.0 multiverse" \
  | tee /etc/apt/sources.list.d/mongodb-org-8.0.list >/dev/null

apt-get update
apt-get install -y mongodb-org
systemctl enable --now mongod

echo "MongoDB version:"
mongod --version | head -n 2
echo "Service active: $(systemctl is-active mongod)"
echo "Service enabled: $(systemctl is-enabled mongod)"

