#!/usr/bin/env bash
set -euo pipefail

# Single integration test for dev DB bootstrap.
# It executes bootstrap and validates representative seeded records.

APP_NAME="${APP_NAME:-cv-match}"
STAGE="${STAGE:-dev}"
REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${STACK_NAME:-${APP_NAME}-${STAGE}-data}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
BOOTSTRAP_SCRIPT="${ROOT_DIR}/infra/deploy/bootstrap-dev-db.sh"

if [[ ! -f "${BOOTSTRAP_SCRIPT}" ]]; then
  echo "bootstrap script not found: ${BOOTSTRAP_SCRIPT}" >&2
  exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

echo "[test] running bootstrap"
APP_NAME="${APP_NAME}" STAGE="${STAGE}" AWS_REGION="${REGION}" STACK_NAME="${STACK_NAME}" SEED_SCOPE="reference" "${BOOTSTRAP_SCRIPT}"

DB_ENDPOINT="$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query "Stacks[0].Outputs[?OutputKey=='DatabaseEndpointAddress'].OutputValue" \
  --output text)"

DB_SECRET_ARN="$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query "Stacks[0].Outputs[?OutputKey=='DatabaseSecretArn'].OutputValue" \
  --output text)"

SECRET_JSON="$(aws secretsmanager get-secret-value \
  --secret-id "${DB_SECRET_ARN}" \
  --region "${REGION}" \
  --query SecretString \
  --output text)"

DATABASE_URL="$(python3 - <<'PY' "${SECRET_JSON}" "${DB_ENDPOINT}"
import json
import sys
from urllib.parse import quote_plus

secret = json.loads(sys.argv[1])
host = sys.argv[2]
username = quote_plus(secret["username"])
password = quote_plus(secret["password"])
port = secret.get("port", 5432)
dbname = secret.get("dbname", "profile_db")
print(f"postgresql://{username}:{password}@{host}:{port}/{dbname}")
PY
)"

echo "[test] validating seeded data"
python3 - <<'PY' "${DATABASE_URL}"
import sys

from psycopg import connect

database_url = sys.argv[1]

expected_min_counts = {
    "countries": 45,
    "regions": 45,
    "cities": 45,
    "skills": 100,
    "roles": 18,
    "degree_types": 8,
}

with connect(database_url) as conn:
    with conn.cursor() as cur:
        for table, minimum in expected_min_counts.items():
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"[test] {table}={count} expected>={minimum}")
            if count < minimum:
                raise AssertionError(f"{table}: expected at least {minimum}, got {count}")

        checks = [
            ("SELECT EXISTS(SELECT 1 FROM countries WHERE code = %s)", "ES", "countries.code=ES"),
            ("SELECT EXISTS(SELECT 1 FROM regions WHERE normalized_name = %s)", "madrid", "regions.normalized_name=madrid"),
            ("SELECT EXISTS(SELECT 1 FROM cities WHERE normalized_name = %s)", "madrid", "cities.normalized_name=madrid"),
            ("SELECT EXISTS(SELECT 1 FROM skills WHERE normalized_skill = %s)", "python", "skills.normalized_skill=python"),
            ("SELECT EXISTS(SELECT 1 FROM roles WHERE normalized_role = %s)", "software engineer", "roles.normalized_role=software engineer"),
            ("SELECT EXISTS(SELECT 1 FROM degree_types WHERE normalized_degree = %s)", "bachelor degree", "degree_types.normalized_degree=bachelor degree"),
        ]

        for sql, value, label in checks:
            cur.execute(sql, (value,))
            ok = cur.fetchone()[0]
            print(f"[test] {label}: {ok}")
            if not ok:
                raise AssertionError(f"missing expected seed: {label}")

print("[test] bootstrap + seed validation passed")
PY
