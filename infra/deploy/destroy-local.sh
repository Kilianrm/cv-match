#!/usr/bin/env bash
set -euo pipefail

# Local teardown workflow for cv-match foundation.
#
# Environment variables:
# - APP_NAME: stack prefix (default: cv-match)
# - STAGE: environment stage (default: dev)
# - DESTROY_SCOPE: data|all (default: data)
# - ENABLE_OBSERVABILITY: true|false (default: false; used when DESTROY_SCOPE=all)

APP_NAME="${APP_NAME:-cv-match}"
STAGE="${STAGE:-dev}"
DESTROY_SCOPE="${DESTROY_SCOPE:-data}"
ENABLE_OBSERVABILITY="${ENABLE_OBSERVABILITY:-false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CDK_DIR="${INFRA_DIR}/cdk"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required" >&2
  exit 1
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "npx is required" >&2
  exit 1
fi

cd "${CDK_DIR}"

echo "[destroy] building CDK app"
npm run build

if [[ "${DESTROY_SCOPE}" == "data" ]]; then
  echo "[destroy] destroying data + network stacks"
  npx cdk destroy \
    "${APP_NAME}-${STAGE}-data" \
    "${APP_NAME}-${STAGE}-network" \
    --force \
    -c stage="${STAGE}" \
    -c appName="${APP_NAME}"
elif [[ "${DESTROY_SCOPE}" == "all" ]]; then
  echo "[destroy] destroying all stacks"
  npx cdk destroy --all \
    --force \
    -c stage="${STAGE}" \
    -c appName="${APP_NAME}" \
    -c enableObservability="${ENABLE_OBSERVABILITY}"
else
  echo "Invalid DESTROY_SCOPE: ${DESTROY_SCOPE}. Use data or all." >&2
  exit 1
fi

echo "[destroy] done"
