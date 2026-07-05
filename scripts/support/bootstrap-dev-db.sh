#!/usr/bin/env bash
set -euo pipefail

# Bootstraps schema and seed catalogs in AWS dev RDS.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/..") && pwd)"

# Load root .env.dev if present (values only apply when not already set in the environment)
if [[ -f "${ROOT_DIR}/.env.dev" ]]; then
	set -a
	# shellcheck source=/dev/null
	source "${ROOT_DIR}/.env.dev"
	set +a
fi

APP_NAME="${APP_NAME:-cv-match}"
STAGE="${STAGE:-dev}"
REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${STACK_NAME:-${APP_NAME}-${STAGE}-data}"
SEED_SCOPE="${SEED_SCOPE:-reference}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOOTSTRAP_SCRIPT="${ROOT_DIR}/support/bootstrap_schema.py"

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

if [[ -z "${DB_ENDPOINT}" || "${DB_ENDPOINT}" == "None" ]]; then
  echo "DatabaseEndpointAddress output not found in stack ${STACK_NAME}" >&2
  exit 1
fi

if [[ -z "${DB_SECRET_ARN}" || "${DB_SECRET_ARN}" == "None" ]]; then
  echo "DatabaseSecretArn output not found in stack ${STACK_NAME}" >&2
  exit 1
fi

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

if "username" not in secret or "password" not in secret:
    raise RuntimeError("secret must contain username and password fields")

username = quote_plus(secret["username"])
password = quote_plus(secret["password"])
port = secret.get("port", 5432)
dbname = secret.get("dbname", "profile_db")
print(f"postgresql://{username}:{password}@{host}:{port}/{dbname}")
PY
)"

echo "Bootstrapping ${STACK_NAME} in ${REGION}"
python3 "${BOOTSTRAP_SCRIPT}" --database-url "${DATABASE_URL}" --seed-scope "${SEED_SCOPE}" --verify
