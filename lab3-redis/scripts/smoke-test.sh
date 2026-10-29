#!/usr/bin/env sh
set -eu

base_url="${BASE_URL:-http://localhost:8000}"

echo "1. Health"
curl --fail --silent --show-error "$base_url/health"
echo

echo "2. First request (cache miss)"
curl --fail --silent --show-error "$base_url/api/v1/users/42/cashback"
echo

echo "3. Second request (cache hit)"
curl --fail --silent --show-error "$base_url/api/v1/users/42/cashback"
echo

echo "4. Transaction changes the user's consumed limits"
curl --fail --silent --show-error \
  -H 'Content-Type: application/json' \
  -d '{"user_id":42,"category":"cafe","amount":1000}' \
  "$base_url/api/v1/transactions"
echo

echo "5. Cache was versioned/invalidate; response is recalculated"
curl --fail --silent --show-error "$base_url/api/v1/users/42/cashback"
echo
