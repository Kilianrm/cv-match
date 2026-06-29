#!/usr/bin/env bash
set -euo pipefail

# Dev deployment orchestration for infrastructure + frontend env sync.
#
# This script coordinates infrastructure deployment in dev and then optionally
# synchronizes frontend environment values from AWS stack outputs.
#
# Environment variables are passed through to infrastructure deployment:
# - APP_NAME, STAGE, AWS_REGION, OPERATION, etc. (see ./infra/scripts/deploy-dev.sh)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
INFRA_DEPLOY_SCRIPT="${ROOT_DIR}/infra/scripts/deploy-dev.sh"
SYNC_FRONTEND_SCRIPT="${ROOT_DIR}/scripts/sync-frontend-env-dev.sh"

OPERATION="${OPERATION:-deploy}"
APP_NAME="${APP_NAME:-cv-match}"
STAGE="${STAGE:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"
LOCAL_FRONTEND_BASE_URL="${LOCAL_FRONTEND_BASE_URL:-http://localhost:3000}"
SYNC_FRONTEND_ENV="${SYNC_FRONTEND_ENV:-false}"
FRONTEND_ENV_FILE="${FRONTEND_ENV_FILE:-${ROOT_DIR}/frontend/.env.aws-dev}"
INFRA_ARGS=()

print_help() {
	cat <<'EOF'
Usage:
	./scripts/deploy-dev.sh [--help] [--destroy] [--destroy-all]

This script orchestrates infrastructure deployment for dev.

Options:
	--destroy          Destroy deployment
	--destroy-all      Destroy all resources
	--help             Show this help message

Infrastructure environment variables (passed through):
	APP_NAME        Stack prefix (default: cv-match)
	STAGE           Environment stage (default: dev)
	AWS_REGION      Deployment region (default: us-east-1)
	OPERATION       deploy|destroy (default: deploy)
	DEPLOY_STACKS   Comma-separated stack names (default: network,security,data)
	USE_SHARED_SECURITY true|false (default: true)
	PUBLIC_DB_ACCESS true|false (default: true)
	RUN_BOOTSTRAP   true|false (default: true)
	RUN_VERIFY      true|false (default: true)
	DEPLOY_STACKS   Optional explicit stack selection override
	LOCAL_FRONTEND_BASE_URL Frontend URL for Cognito callback/logout defaults (default: http://localhost:3000)
	SYNC_FRONTEND_ENV true|false to generate frontend env from AWS outputs (default: false)
	FRONTEND_ENV_FILE Target frontend env file path for sync (default: frontend/.env.aws-dev)

Examples:
	./scripts/deploy-dev.sh                    # Deploy infra
	./scripts/deploy-dev.sh --destroy-all      # Destroy everything
EOF
}

log() {
	local message="$1"
	echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [deploy] ${message}"
}

validate_bool() {
	local name="$1"
	local value="$2"
	if [[ "${value}" != "true" && "${value}" != "false" ]]; then
		echo "Invalid ${name}: ${value}. Use true or false." >&2
		exit 1
	fi
}

on_error() {
	local exit_code=$?
	log "FAILED (exit code: ${exit_code})"
	exit ${exit_code}
}

trap on_error ERR

# Parse command-line arguments
for arg in "$@"; do
	case "$arg" in
		-h|--help|help)
			print_help
			exit 0
			;;
		--destroy)
			OPERATION="destroy"
			INFRA_ARGS+=("$arg")
			;;
		--destroy-all)
			OPERATION="destroy"
			DESTROY_ALL="true"
			INFRA_ARGS+=("$arg")
			;;
		*)
			echo "Unsupported argument: ${arg}" >&2
			print_help >&2
			exit 1
			;;
	esac
done

validate_bool "SYNC_FRONTEND_ENV" "${SYNC_FRONTEND_ENV}"

log "starting dev deployment orchestration"
log "config: operation=${OPERATION}, deploy_stacks=${DEPLOY_STACKS:-inherit}, sync_frontend_env=${SYNC_FRONTEND_ENV}, frontend_env_file=${FRONTEND_ENV_FILE}"

if [[ ! -f "${INFRA_DEPLOY_SCRIPT}" ]]; then
	log "ERROR: infrastructure deploy script not found: ${INFRA_DEPLOY_SCRIPT}"
	exit 1
fi

log "delegating to infrastructure deployment"

# Pass through environment variables to infra script
if [[ -n "${DEPLOY_STACKS:-}" ]]; then
	APP_NAME="${APP_NAME}" STAGE="${STAGE}" AWS_REGION="${AWS_REGION}" \
	LOCAL_FRONTEND_BASE_URL="${LOCAL_FRONTEND_BASE_URL}" DEPLOY_STACKS="${DEPLOY_STACKS}" \
	bash "${INFRA_DEPLOY_SCRIPT}" "${INFRA_ARGS[@]}"
else
	APP_NAME="${APP_NAME}" STAGE="${STAGE}" AWS_REGION="${AWS_REGION}" \
	LOCAL_FRONTEND_BASE_URL="${LOCAL_FRONTEND_BASE_URL}" \
	bash "${INFRA_DEPLOY_SCRIPT}" "${INFRA_ARGS[@]}"
fi

if [[ "${OPERATION}" == "deploy" && "${SYNC_FRONTEND_ENV}" == "true" ]]; then
	if [[ ! -f "${SYNC_FRONTEND_SCRIPT}" ]]; then
		log "ERROR: frontend sync script not found: ${SYNC_FRONTEND_SCRIPT}"
		exit 1
	fi

	log "syncing frontend env file: ${FRONTEND_ENV_FILE}"
	APP_NAME="${APP_NAME}" STAGE="${STAGE}" AWS_REGION="${AWS_REGION}" \
	LOCAL_FRONTEND_BASE_URL="${LOCAL_FRONTEND_BASE_URL}" FRONTEND_ENV_FILE="${FRONTEND_ENV_FILE}" \
	bash "${SYNC_FRONTEND_SCRIPT}"
	log "frontend env sync complete"
fi

log "deployment orchestration complete"
