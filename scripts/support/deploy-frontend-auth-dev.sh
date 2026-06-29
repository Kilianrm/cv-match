#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SYNC_SCRIPT="${ROOT_DIR}/scripts/support/sync-frontend-auth-dev.sh"
CDK_DIR="${ROOT_DIR}/infra/cdk"

APP_NAME="${APP_NAME:-cv-match}"
STAGE="${STAGE:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"
LOCAL_FRONTEND_BASE_URL="${LOCAL_FRONTEND_BASE_URL:-http://localhost:3000}"
FRONTEND_ENV_FILE="${FRONTEND_ENV_FILE:-${ROOT_DIR}/frontend/.env.aws-dev}"
CDK_ENTRYPOINT="${CDK_DIR}/dist/bin/cdk.js"

log() {
	local message="$1"
	echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [deploy-frontend-auth-dev] ${message}"
}

cdk_build_required() {
	if [[ ! -f "${CDK_ENTRYPOINT}" ]]; then
		return 0
	fi

	if find "${CDK_DIR}/bin" "${CDK_DIR}/lib" -type f \( -name '*.ts' -o -name 'package.json' -o -name 'tsconfig.json' -o -name 'cdk.json' \) -newer "${CDK_ENTRYPOINT}" | grep -q .; then
		return 0
	fi

	return 1
}

print_help() {
	cat <<'EOF'
Usage:
	./scripts/support/deploy-frontend-auth-dev.sh [--help] [--destroy] [--destroy-all]

This support script is for conceptual local frontend testing with AWS dev
authentication only.

What it deploys:
	DEPLOY_STACKS=network,auth

What it does after deploy:
	Syncs frontend auth environment values from the auth stack only

Options:
	--destroy          Destroy the selected support stacks
	--destroy-all      Destroy all stacks through the underlying deploy flow
	--help             Show this help message
EOF
}

if [[ ! -d "${CDK_DIR}" ]]; then
	log "ERROR: CDK directory not found: ${CDK_DIR}"
	exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
	echo "npm is required" >&2
	exit 1
fi

if ! command -v npx >/dev/null 2>&1; then
	echo "npx is required" >&2
	exit 1
fi

for arg in "$@"; do
	case "$arg" in
		-h|--help|help)
			print_help
			exit 0
			;;
		--destroy|--destroy-all)
			;;
		*)
			echo "Unsupported argument: ${arg}" >&2
			print_help >&2
			exit 1
			;;
	esac
done

network_stack="${APP_NAME}-${STAGE}-network"
auth_stack="${APP_NAME}-${STAGE}-auth"

cd "${CDK_DIR}"
if cdk_build_required; then
	log "building CDK app"
	npm run build
else
	log "reusing existing CDK build"
fi

if [[ "${1:-}" == "--destroy-all" ]]; then
	log "destroying all CDK stacks"
	npx cdk destroy --all \
		--force \
		-c stage="${STAGE}" \
		-c appName="${APP_NAME}" \
		-c localFrontendBaseUrl="${LOCAL_FRONTEND_BASE_URL}"
	log "destroy complete"
	exit 0
fi

if [[ "${1:-}" == "--destroy" ]]; then
	log "destroying support stacks: ${network_stack} ${auth_stack}"
	npx cdk destroy \
		"${auth_stack}" \
		"${network_stack}" \
		--force \
		-c stage="${STAGE}" \
		-c appName="${APP_NAME}" \
		-c localFrontendBaseUrl="${LOCAL_FRONTEND_BASE_URL}"
	log "destroy complete"
	exit 0
fi

log "deploying support stacks: ${network_stack} ${auth_stack}"
	npx cdk deploy \
		"${network_stack}" \
		"${auth_stack}" \
		--require-approval never \
		-c stage="${STAGE}" \
		-c appName="${APP_NAME}" \
		-c localFrontendBaseUrl="${LOCAL_FRONTEND_BASE_URL}"

	APP_NAME="${APP_NAME}" \
	STAGE="${STAGE}" \
	AWS_REGION="${AWS_REGION}" \
	LOCAL_FRONTEND_BASE_URL="${LOCAL_FRONTEND_BASE_URL}" \
	FRONTEND_ENV_FILE="${FRONTEND_ENV_FILE}" \
	bash "${SYNC_SCRIPT}"