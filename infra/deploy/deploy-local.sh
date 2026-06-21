#!/usr/bin/env bash
set -euo pipefail

# Local deployment workflow for cv-match foundation + DB bootstrap.
#
# Defaults are optimized for Step 4 (data flow):
# 1) deploy network + data stacks
# 2) bootstrap schema/seeds
# 3) verify bootstrap
#
# Environment variables:
# - APP_NAME: stack prefix (default: cv-match)
# - STAGE: environment stage (default: dev)
# - AWS_REGION: deployment region (default: us-east-1)
# - DEPLOY_SCOPE: data|all (default: data)
# - ENABLE_OBSERVABILITY: true|false (default: false; used when DEPLOY_SCOPE=all)
# - SEED_SCOPE: reference|dev|all (default: reference)

APP_NAME="${APP_NAME:-cv-match}"
STAGE="${STAGE:-dev}"
REGION="${AWS_REGION:-us-east-1}"
DEPLOY_SCOPE="${DEPLOY_SCOPE:-data}"
ENABLE_OBSERVABILITY="${ENABLE_OBSERVABILITY:-false}"
SEED_SCOPE="${SEED_SCOPE:-reference}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CDK_DIR="${INFRA_DIR}/cdk"

CURRENT_STEP="initializing"

log() {
  local message="$1"
  echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [deploy] ${message}"
}

on_error() {
  local exit_code=$?
  log "FAILED at step: ${CURRENT_STEP} (exit code: ${exit_code})"
  exit ${exit_code}
}

trap on_error ERR

log "starting local deployment workflow"
log "config: app=${APP_NAME}, stage=${STAGE}, region=${REGION}, deploy_scope=${DEPLOY_SCOPE}, seed_scope=${SEED_SCOPE}, observability=${ENABLE_OBSERVABILITY}"

CURRENT_STEP="checking aws CLI"
if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required" >&2
  exit 1
fi
log "aws CLI found"

CURRENT_STEP="checking npm"
if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required" >&2
  exit 1
fi
log "npm found"

CURRENT_STEP="checking npx"
if ! command -v npx >/dev/null 2>&1; then
  echo "npx is required" >&2
  exit 1
fi
log "npx found"

CURRENT_STEP="changing directory to CDK"
cd "${CDK_DIR}"
log "working directory: ${CDK_DIR}"

CURRENT_STEP="building CDK app"
log "building CDK app"
npm run build
log "CDK build complete"

if [[ "${DEPLOY_SCOPE}" == "data" ]]; then
  CURRENT_STEP="deploying network and data stacks"
  log "deploying network + data stacks (${APP_NAME}-${STAGE}-network, ${APP_NAME}-${STAGE}-data)"
  npx cdk deploy \
    "${APP_NAME}-${STAGE}-network" \
    "${APP_NAME}-${STAGE}-data" \
    --require-approval never \
    -c stage="${STAGE}" \
    -c appName="${APP_NAME}"
  log "network + data deployment complete"
elif [[ "${DEPLOY_SCOPE}" == "all" ]]; then
  CURRENT_STEP="deploying all stacks"
  log "deploying all stacks"
  npx cdk deploy --all \
    --require-approval never \
    -c stage="${STAGE}" \
    -c appName="${APP_NAME}" \
    -c enableObservability="${ENABLE_OBSERVABILITY}"
  log "all stacks deployment complete"
else
  echo "Invalid DEPLOY_SCOPE: ${DEPLOY_SCOPE}. Use data or all." >&2
  exit 1
fi

CURRENT_STEP="bootstrapping database"
log "bootstrapping database (seed scope: ${SEED_SCOPE})"
APP_NAME="${APP_NAME}" STAGE="${STAGE}" AWS_REGION="${REGION}" SEED_SCOPE="${SEED_SCOPE}" "${INFRA_DIR}/deploy/bootstrap-dev-db.sh"
log "database bootstrap complete"

CURRENT_STEP="verifying bootstrap"
log "verifying bootstrap"
APP_NAME="${APP_NAME}" STAGE="${STAGE}" AWS_REGION="${REGION}" ./test/integration/bootstrap-dev-db.test.sh
log "bootstrap verification complete"

CURRENT_STEP="done"
log "done"
