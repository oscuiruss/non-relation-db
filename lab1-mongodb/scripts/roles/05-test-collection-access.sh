#!/usr/bin/env bash
set -Eeuo pipefail

common=(
  --host 127.0.0.1
  --port 27017
  --username grades_reader
  --authenticationDatabase university
  --password
  --quiet
)

echo "1. Reading university.grades must succeed"
mongosh "${common[@]}" \
  --eval 'printjson(db.getSiblingDB("university").grades.findOne())'

echo "2. Reading university.students must be denied"
echo "Введите тот же пароль ещё раз."
if mongosh "${common[@]}" \
  --eval 'printjson(db.getSiblingDB("university").students.findOne())'; then
  echo "ERROR: access to university.students was unexpectedly allowed" >&2
  exit 1
else
  echo "OK: access to university.students was denied"
fi
