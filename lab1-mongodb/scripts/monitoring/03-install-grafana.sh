#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
grafana_config="$(cd "$script_dir/../../config/grafana" && pwd)"

apt-get install -y apt-transport-https wget gnupg
install -d -m 0755 /etc/apt/keyrings
wget -q -O /etc/apt/keyrings/grafana.asc https://apt.grafana.com/gpg-full.key
chmod 0644 /etc/apt/keyrings/grafana.asc
echo 'deb [signed-by=/etc/apt/keyrings/grafana.asc] https://apt.grafana.com stable main' \
  | tee /etc/apt/sources.list.d/grafana.list >/dev/null

apt-get update
apt-get install -y grafana

install -d -m 0755 /etc/grafana/provisioning/datasources
install -d -m 0755 /etc/grafana/provisioning/dashboards
install -d -m 0755 -o grafana -g grafana /var/lib/grafana/dashboards
install -m 0644 "$grafana_config/provisioning/datasources/prometheus.yml" \
  /etc/grafana/provisioning/datasources/prometheus.yml
install -m 0644 "$grafana_config/provisioning/dashboards/mongodb.yml" \
  /etc/grafana/provisioning/dashboards/mongodb.yml
install -m 0644 "$grafana_config/dashboards/mongodb-lab.json" \
  /var/lib/grafana/dashboards/mongodb-lab.json
chown grafana:grafana /var/lib/grafana/dashboards/mongodb-lab.json

systemctl enable --now grafana-server
systemctl restart grafana-server
systemctl status grafana-server --no-pager

echo "Open http://<VM-IP>:3000 (initial login: admin/admin)"

