#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
config_dir="$(cd "$script_dir/../../config" && pwd)"

apt-get update
apt-get install -y prometheus
install -m 0644 "$config_dir/prometheus.yml" /etc/prometheus/prometheus.yml
promtool check config /etc/prometheus/prometheus.yml
systemctl enable --now prometheus
systemctl restart prometheus
systemctl status prometheus --no-pager

