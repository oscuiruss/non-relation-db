#!/usr/bin/env bash
set -euo pipefail

umask 077

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
pki_dir="${project_dir}/files/pki"

if [[ -e "${pki_dir}/root-ca-key.pem" ]]; then
  echo "PKI already exists in ${pki_dir}. Nothing was overwritten."
  exit 1
fi

mkdir -p "${pki_dir}"

issue_certificate() {
  local name="$1"
  local subject="$2"
  local extended_key_usage="$3"
  local subject_alt_name="${4:-}"
  local extension_file="${pki_dir}/${name}.ext"

  openssl genpkey \
    -algorithm RSA \
    -pkeyopt rsa_keygen_bits:2048 \
    -out "${pki_dir}/${name}-key.pem"

  openssl req \
    -new \
    -sha256 \
    -key "${pki_dir}/${name}-key.pem" \
    -subj "${subject}" \
    -out "${pki_dir}/${name}.csr"

  {
    echo "basicConstraints=critical,CA:FALSE"
    echo "keyUsage=critical,digitalSignature,keyEncipherment"
    echo "extendedKeyUsage=${extended_key_usage}"
    if [[ -n "${subject_alt_name}" ]]; then
      echo "subjectAltName=${subject_alt_name}"
    fi
  } > "${extension_file}"

  openssl x509 \
    -req \
    -sha256 \
    -days 730 \
    -in "${pki_dir}/${name}.csr" \
    -CA "${pki_dir}/root-ca.pem" \
    -CAkey "${pki_dir}/root-ca-key.pem" \
    -CAserial "${pki_dir}/root-ca.srl" \
    -CAcreateserial \
    -extfile "${extension_file}" \
    -out "${pki_dir}/${name}.pem"

  rm "${pki_dir}/${name}.csr" "${extension_file}"
}

openssl genpkey \
  -algorithm RSA \
  -pkeyopt rsa_keygen_bits:4096 \
  -out "${pki_dir}/root-ca-key.pem"

openssl req \
  -new \
  -x509 \
  -sha256 \
  -days 730 \
  -key "${pki_dir}/root-ca-key.pem" \
  -subj "/C=RU/O=OpenSearch Lab/CN=OpenSearch Lab Root CA" \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" \
  -addext "subjectKeyIdentifier=hash" \
  -out "${pki_dir}/root-ca.pem"

issue_certificate \
  "admin" \
  "/C=RU/O=OpenSearch Lab/OU=Security/CN=opensearch-admin" \
  "clientAuth"

issue_certificate \
  "os-hot" \
  "/C=RU/O=OpenSearch Lab/OU=Nodes/CN=os-hot" \
  "serverAuth,clientAuth" \
  "DNS:os-hot,IP:192.168.60.135,IP:127.0.0.1"

issue_certificate \
  "os-warm" \
  "/C=RU/O=OpenSearch Lab/OU=Nodes/CN=os-warm" \
  "serverAuth,clientAuth" \
  "DNS:os-warm,IP:192.168.60.134,IP:127.0.0.1"

chmod 0600 "${pki_dir}"/*-key.pem
chmod 0644 "${pki_dir}"/*.pem

for certificate in admin os-hot os-warm; do
  openssl verify \
    -CAfile "${pki_dir}/root-ca.pem" \
    "${pki_dir}/${certificate}.pem"
done

echo
echo "Generated certificate subjects:"
for certificate in root-ca admin os-hot os-warm; do
  openssl x509 \
    -in "${pki_dir}/${certificate}.pem" \
    -subject \
    -nameopt RFC2253 \
    -noout
done

echo
echo "Certificates were generated in ${pki_dir}"
