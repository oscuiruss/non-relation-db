#!/usr/bin/env bash
set -euo pipefail

umask 077

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
pki_dir="${project_dir}/files/pki"
certificate_name="opensearch-dashboards"

for required_file in root-ca.pem root-ca-key.pem root-ca.srl; do
  if [[ ! -f "${pki_dir}/${required_file}" ]]; then
    echo "Missing ${pki_dir}/${required_file}. Generate the lab CA first."
    exit 1
  fi
done

if [[ -e "${pki_dir}/${certificate_name}.pem" || -e "${pki_dir}/${certificate_name}-key.pem" ]]; then
  echo "The OpenSearch Dashboards certificate already exists. Nothing was overwritten."
  exit 1
fi

extension_file="${pki_dir}/${certificate_name}.ext"
request_file="${pki_dir}/${certificate_name}.csr"

openssl genpkey \
  -algorithm RSA \
  -pkeyopt rsa_keygen_bits:2048 \
  -out "${pki_dir}/${certificate_name}-key.pem"

openssl req \
  -new \
  -sha256 \
  -key "${pki_dir}/${certificate_name}-key.pem" \
  -subj "/C=RU/O=OpenSearch Lab/OU=Dashboards/CN=os-hot" \
  -out "${request_file}"

{
  echo "basicConstraints=critical,CA:FALSE"
  echo "keyUsage=critical,digitalSignature,keyEncipherment"
  echo "extendedKeyUsage=serverAuth"
  echo "subjectAltName=DNS:os-hot,IP:192.168.60.135,IP:127.0.0.1"
} > "${extension_file}"

openssl x509 \
  -req \
  -sha256 \
  -days 730 \
  -in "${request_file}" \
  -CA "${pki_dir}/root-ca.pem" \
  -CAkey "${pki_dir}/root-ca-key.pem" \
  -CAserial "${pki_dir}/root-ca.srl" \
  -extfile "${extension_file}" \
  -out "${pki_dir}/${certificate_name}.pem"

rm "${request_file}" "${extension_file}"
chmod 0600 "${pki_dir}/${certificate_name}-key.pem"
chmod 0644 "${pki_dir}/${certificate_name}.pem"

openssl verify \
  -CAfile "${pki_dir}/root-ca.pem" \
  "${pki_dir}/${certificate_name}.pem"

openssl x509 \
  -in "${pki_dir}/${certificate_name}.pem" \
  -subject \
  -ext subjectAltName \
  -noout

echo "OpenSearch Dashboards certificate generated in ${pki_dir}."
