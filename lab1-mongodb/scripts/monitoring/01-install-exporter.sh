#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi

version="0.53.0"
architecture="$(dpkg --print-architecture)"
case "$architecture" in
  arm64) asset_arch=arm64 ;;
  amd64) asset_arch=amd64 ;;
  *) echo "Unsupported architecture: $architecture" >&2; exit 1 ;;
esac

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
config_dir="$(cd "$script_dir/../../config" && pwd)"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

url="https://github.com/percona/mongodb_exporter/releases/download/v${version}/mongodb_exporter-${version}.linux-${asset_arch}.tar.gz"
curl -fL "$url" -o "$work_dir/exporter.tar.gz"
tar -xzf "$work_dir/exporter.tar.gz" -C "$work_dir"
binary="$(find "$work_dir" -type f -name mongodb_exporter | head -n 1)"
if [[ -z "$binary" ]]; then
  echo "mongodb_exporter binary not found in release archive" >&2
  exit 1
fi
install -m 0755 "$binary" /usr/local/bin/mongodb_exporter

if ! id mongodb-exporter >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin mongodb-exporter
fi

install -d -m 0750 -o root -g mongodb-exporter /etc/mongodb-exporter
read -r -s -p 'Password for MongoDB user mongodb_exporter: ' exporter_password
echo
escaped_password="${exporter_password//\\/\\\\}"
escaped_password="${escaped_password//\"/\\\"}"
{
  echo 'MONGODB_USER=mongodb_exporter'
  printf 'MONGODB_PASSWORD="%s"\n' "$escaped_password"
} >/etc/mongodb-exporter/mongodb-exporter.env
chown root:mongodb-exporter /etc/mongodb-exporter/mongodb-exporter.env
chmod 0640 /etc/mongodb-exporter/mongodb-exporter.env

install -m 0644 "$config_dir/mongodb-exporter.service" /etc/systemd/system/mongodb-exporter.service
systemctl daemon-reload
systemctl enable --now mongodb-exporter
systemctl status mongodb-exporter --no-pager

echo "Metrics: http://127.0.0.1:9216/metrics"
