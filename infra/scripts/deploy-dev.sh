#!/usr/bin/env bash
set -euo pipefail

# Dev deployment workflow for cv-match foundation + DB bootstrap.
#
# Optional post-deploy actions for data flow:
# 1) deploy base infra + shared infra stacks
# 2) bootstrap schema/seeds
# 3) verify bootstrap
#
# Environment variables:
# - APP_NAME: stack prefix (default: cv-match)
# - STAGE: environment stage (default: dev)
# - AWS_REGION: deployment region (default: us-east-1)
# - OPERATION: deploy|destroy (default: deploy)
# - DESTROY_ALL: true|false (default: false)
# - DEPLOY_STACKS: comma-separated stack selectors (default: network,security,compute,data)
#   Accepts full stack names (cv-match-dev-network), stack selectors (network), or file-style names (network.ts/network-stack.ts)
# - USE_SHARED_SECURITY: true|false (default: true)
# - PUBLIC_DB_ACCESS: true|false (default: true)
# - PUBLIC_DB_ACCESS_CIDR: IPv4 CIDR allowed to connect to PostgreSQL when public DB access is enabled.
#   If omitted and PUBLIC_DB_ACCESS=true, script resolves caller public IP and uses /32.
# - PROFILE_SERVICE_BASE_URL: optional override for gateway -> profile-service calls.
#   Default uses the ECS Service Connect client alias: http://profile-service:8080
# - LOCAL_FRONTEND_BASE_URL: frontend URL used for Cognito callback/logout defaults (default: http://localhost:3000)
# - COGNITO_DOMAIN_PREFIX: optional explicit Cognito Hosted UI domain prefix.
# - SEED_SCOPE: reference|dev|all (default: reference)
# - RUN_BOOTSTRAP: true|false (default: false)
# - RUN_VERIFY: true|false (default: false)
# - FORCE_DEPLOY: true|false (default: false). Adds `--force` to `cdk deploy`.

APP_NAME="${APP_NAME:-cv-match}"
STAGE="${STAGE:-dev}"
REGION="${AWS_REGION:-us-east-1}"
OPERATION="${OPERATION:-deploy}"
DESTROY_ALL="${DESTROY_ALL:-false}"
DEPLOY_STACKS="${DEPLOY_STACKS:-network,security,compute,data}"
USE_SHARED_SECURITY="${USE_SHARED_SECURITY:-true}"
PUBLIC_DB_ACCESS="${PUBLIC_DB_ACCESS:-true}"
PUBLIC_DB_ACCESS_CIDR="${PUBLIC_DB_ACCESS_CIDR:-}"
PROFILE_SERVICE_BASE_URL="${PROFILE_SERVICE_BASE_URL:-http://profile-service:8080}"
LOCAL_FRONTEND_BASE_URL="${LOCAL_FRONTEND_BASE_URL:-http://localhost:3000}"
COGNITO_DOMAIN_PREFIX="${COGNITO_DOMAIN_PREFIX:-}"
SEED_SCOPE="${SEED_SCOPE:-reference}"
RUN_BOOTSTRAP="${RUN_BOOTSTRAP:-false}"
RUN_VERIFY="${RUN_VERIFY:-false}"
FORCE_DEPLOY="${FORCE_DEPLOY:-false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INFRA_DIR="${ROOT_DIR}/infra"
CDK_DIR="${INFRA_DIR}/cdk"

CURRENT_STEP="initializing"

print_help() {
	cat <<'EOF'
Usage:
	./scripts/deploy-dev.sh [--help] [--destroy] [--destroy-all] [--force-deploy]

This script is configured through environment variables.

Environment variables:
	APP_NAME        Stack prefix (default: cv-match)
	STAGE           Environment stage (default: dev)
	AWS_REGION      Deployment region (default: us-east-1)
	OPERATION       deploy|destroy (default: deploy)
	DESTROY_ALL     true|false (default: false)
	DEPLOY_STACKS   Comma-separated stack names (default: network,security,compute,data)
									Accepts: network, security, compute, data, auth, profile, gateway,
									file-style values (network.ts, network-stack.ts),
									or full stack names (cv-match-dev-network)
	USE_SHARED_SECURITY true|false (default: true)
	PUBLIC_DB_ACCESS true|false (default: false)
	PUBLIC_DB_ACCESS_CIDR IPv4 CIDR for PostgreSQL ingress when PUBLIC_DB_ACCESS=true
	PROFILE_SERVICE_BASE_URL Optional gateway override for profile-service URL (default: http://profile-service:8080)
	LOCAL_FRONTEND_BASE_URL Frontend base URL for Cognito callback/logout (default: http://localhost:3000)
	COGNITO_DOMAIN_PREFIX Optional explicit Cognito hosted domain prefix
	SEED_SCOPE      reference|dev|all (default: reference)
	RUN_BOOTSTRAP   true|false (default: false)
	RUN_VERIFY      true|false (default: false)
	FORCE_DEPLOY    true|false (default: false). Adds --force to cdk deploy.

Examples:
	./scripts/deploy-dev.sh
	./scripts/deploy-dev.sh --destroy-all
	DEPLOY_STACKS=network,security,compute,data ./scripts/deploy-dev.sh
	DEPLOY_STACKS=network,security,compute,data,auth,profile,gateway ./scripts/deploy-dev.sh
	PROFILE_SERVICE_BASE_URL=http://profile-service:8080 DEPLOY_STACKS=network,security,compute,data,profile,gateway ./scripts/deploy-dev.sh
	DEPLOY_STACKS=network RUN_BOOTSTRAP=false RUN_VERIFY=false ./scripts/deploy-dev.sh
	DEPLOY_STACKS=full RUN_BOOTSTRAP=true RUN_VERIFY=true ./scripts/deploy-dev.sh
	DEPLOY_STACKS=cv-match-dev-network ./scripts/deploy-dev.sh
EOF
}

for arg in "$@"; do
	case "$arg" in
		-h|--help|help)
			print_help
			exit 0
			;;
		--destroy)
			OPERATION="destroy"
			;;
		--destroy-all)
			OPERATION="destroy"
			DESTROY_ALL="true"
			;;
		--force-deploy)
			FORCE_DEPLOY="true"
			;;
		*)
			echo "Unsupported argument: ${arg}" >&2
			print_help >&2
			exit 1
			;;
	esac
done

log() {
	local message="$1"
	echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [deploy-dev] ${message}"
}

on_error() {
	local exit_code=$?
	log "FAILED at step: ${CURRENT_STEP} (exit code: ${exit_code})"
	exit ${exit_code}
}

trap on_error ERR

log "starting dev deployment workflow"
log "config: app=${APP_NAME}, stage=${STAGE}, region=${REGION}, operation=${OPERATION}, destroy_all=${DESTROY_ALL}, force_deploy=${FORCE_DEPLOY}, deploy_stacks=${DEPLOY_STACKS}, use_shared_security=${USE_SHARED_SECURITY}, public_db_access=${PUBLIC_DB_ACCESS}, public_db_access_cidr=${PUBLIC_DB_ACCESS_CIDR:-auto}, profile_service_base_url=${PROFILE_SERVICE_BASE_URL:-auto}, local_frontend_base_url=${LOCAL_FRONTEND_BASE_URL}, cognito_domain_prefix=${COGNITO_DOMAIN_PREFIX:-auto}, seed_scope=${SEED_SCOPE}, run_bootstrap=${RUN_BOOTSTRAP}, run_verify=${RUN_VERIFY}"

validate_bool() {
	local name="$1"
	local value="$2"
	if [[ "${value}" != "true" && "${value}" != "false" ]]; then
		echo "Invalid ${name}: ${value}. Use true or false." >&2
		exit 1
	fi
}

validate_bool "RUN_BOOTSTRAP" "${RUN_BOOTSTRAP}"
validate_bool "RUN_VERIFY" "${RUN_VERIFY}"
validate_bool "DESTROY_ALL" "${DESTROY_ALL}"
validate_bool "USE_SHARED_SECURITY" "${USE_SHARED_SECURITY}"
validate_bool "PUBLIC_DB_ACCESS" "${PUBLIC_DB_ACCESS}"
validate_bool "FORCE_DEPLOY" "${FORCE_DEPLOY}"

if [[ "${PUBLIC_DB_ACCESS}" == "true" && "${STAGE}" != "dev" ]]; then
	echo "PUBLIC_DB_ACCESS is only allowed when STAGE=dev" >&2
	exit 1
fi

if [[ "${PUBLIC_DB_ACCESS}" == "true" && -z "${PUBLIC_DB_ACCESS_CIDR}" ]]; then
	if ! command -v curl >/dev/null 2>&1; then
		echo "curl is required to auto-resolve PUBLIC_DB_ACCESS_CIDR when PUBLIC_DB_ACCESS=true" >&2
		exit 1
	fi

	resolved_ip="$(curl -fsS https://checkip.amazonaws.com | tr -d '[:space:]')"
	if [[ -z "${resolved_ip}" ]]; then
		echo "Failed to resolve public IP for PUBLIC_DB_ACCESS_CIDR" >&2
		exit 1
	fi

	PUBLIC_DB_ACCESS_CIDR="${resolved_ip}/32"
	log "resolved PUBLIC_DB_ACCESS_CIDR=${PUBLIC_DB_ACCESS_CIDR}"
fi

if [[ "${OPERATION}" != "deploy" && "${OPERATION}" != "destroy" ]]; then
	echo "Invalid OPERATION: ${OPERATION}. Use deploy or destroy." >&2
	exit 1
fi

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

resolve_stack_name() {
	local selector="$1"

	if [[ "${selector}" == "${APP_NAME}-${STAGE}-"* ]]; then
		echo "${selector}"
		return 0
	fi

	local normalized="${selector##*/}"
	normalized="${normalized%.ts}"
	normalized="${normalized%-stack}"

	case "${normalized}" in
		network)
			echo "${APP_NAME}-${STAGE}-network"
			;;
		security)
			echo "${APP_NAME}-${STAGE}-security"
			;;
		compute)
			echo "${APP_NAME}-${STAGE}-compute"
			;;
		data)
			echo "${APP_NAME}-${STAGE}-data"
			;;
		auth)
			echo "${APP_NAME}-${STAGE}-auth"
			;;
		profile)
			echo "${APP_NAME}-${STAGE}-profile"
			;;
		gateway)
			echo "${APP_NAME}-${STAGE}-gateway"
			;;
		*)
			echo "${APP_NAME}-${STAGE}-${normalized}"
			;;
	esac
}

CURRENT_STEP="deploying selected stacks"
IFS=',' read -r -a raw_stacks <<< "${DEPLOY_STACKS}"
selected_stacks=()
declare -A seen_stacks=()
for stack in "${raw_stacks[@]}"; do
	trimmed_stack="$(echo "${stack}" | xargs)"
	if [[ -z "${trimmed_stack}" ]]; then
		continue
	fi
	resolved_stack="$(resolve_stack_name "${trimmed_stack}")"
	if [[ -z "${seen_stacks[${resolved_stack}]+x}" ]]; then
		seen_stacks["${resolved_stack}"]=1
		selected_stacks+=("${resolved_stack}")
	fi
done

if [[ ${#selected_stacks[@]} -eq 0 ]]; then
	echo "DEPLOY_STACKS resolved to an empty list. Provide at least one stack name." >&2
	exit 1
fi

data_stack_name="${APP_NAME}-${STAGE}-data"
data_selected="false"
for stack in "${selected_stacks[@]}"; do
	if [[ "${stack}" == "${data_stack_name}" ]]; then
		data_selected="true"
	fi
done

deploy_cdk_stacks() {
	local profile_url="$1"
	shift
	local stacks_to_deploy=("$@")

	if [[ ${#stacks_to_deploy[@]} -eq 0 ]]; then
		return 0
	fi

	local cdk_args=(
		npx cdk deploy
		"${stacks_to_deploy[@]}"
		--require-approval never
		-c stage="${STAGE}"
		-c appName="${APP_NAME}"
		-c useSharedSecurity="${USE_SHARED_SECURITY}"
		-c publicDatabaseAccess="${PUBLIC_DB_ACCESS}"
		-c publicDatabaseAccessCidr="${PUBLIC_DB_ACCESS_CIDR}"
		-c localFrontendBaseUrl="${LOCAL_FRONTEND_BASE_URL}"
	)

	if [[ "${FORCE_DEPLOY}" == "true" ]]; then
		cdk_args+=( --force )
	fi

	if [[ -n "${COGNITO_DOMAIN_PREFIX}" ]]; then
		cdk_args+=( -c "cognitoDomainPrefix=${COGNITO_DOMAIN_PREFIX}" )
	fi

	if [[ -n "${profile_url}" ]]; then
		cdk_args+=( -c "profileServiceBaseUrl=${profile_url}" )
	fi

	"${cdk_args[@]}"
}

if [[ "${OPERATION}" == "deploy" ]]; then
	profile_service_url_override="${PROFILE_SERVICE_BASE_URL}"
	log "using gateway profile service base url: ${profile_service_url_override}"
	log "deploying selected stacks: ${selected_stacks[*]}"
	deploy_cdk_stacks "${profile_service_url_override}" "${selected_stacks[@]}"
	log "selected stack deployment complete"

else
	if [[ "${DESTROY_ALL}" == "true" ]]; then
		log "destroying all stacks in ${APP_NAME}-${STAGE} scope"
		npx cdk destroy --all \
			--force \
			-c stage="${STAGE}" \
			-c appName="${APP_NAME}" \
			-c useSharedSecurity="${USE_SHARED_SECURITY}" \
			-c publicDatabaseAccess="${PUBLIC_DB_ACCESS}" \
			-c publicDatabaseAccessCidr="${PUBLIC_DB_ACCESS_CIDR}"
		log "all stacks destroyed"
	else
		log "destroying selected stacks: ${selected_stacks[*]}"
		npx cdk destroy \
			"${selected_stacks[@]}" \
			--force \
			-c stage="${STAGE}" \
			-c appName="${APP_NAME}" \
			-c useSharedSecurity="${USE_SHARED_SECURITY}" \
			-c publicDatabaseAccess="${PUBLIC_DB_ACCESS}" \
			-c publicDatabaseAccessCidr="${PUBLIC_DB_ACCESS_CIDR}"
		log "selected stack destroy complete"
	fi
fi

if [[ "${OPERATION}" == "deploy" && "${RUN_BOOTSTRAP}" == "true" && "${data_selected}" == "true" ]]; then
	CURRENT_STEP="bootstrapping database"
	log "bootstrapping database (seed scope: ${SEED_SCOPE})"
	APP_NAME="${APP_NAME}" STAGE="${STAGE}" AWS_REGION="${REGION}" SEED_SCOPE="${SEED_SCOPE}" "${ROOT_DIR}/scripts/support/bootstrap-dev-db.sh"
	log "database bootstrap complete"
elif [[ "${OPERATION}" == "deploy" && "${RUN_BOOTSTRAP}" == "false" ]]; then
	log "skipping database bootstrap"
elif [[ "${OPERATION}" == "deploy" && "${data_selected}" != "true" ]]; then
	log "skipping database bootstrap (data stack not selected)"
fi

if [[ "${OPERATION}" == "deploy" && "${RUN_VERIFY}" == "true" && "${data_selected}" == "true" ]]; then
	CURRENT_STEP="verifying bootstrap"
	log "verifying bootstrap"
	APP_NAME="${APP_NAME}" STAGE="${STAGE}" AWS_REGION="${REGION}" "${ROOT_DIR}/tests/integration/bootstrap-dev-db.test.sh"
	log "bootstrap verification complete"
elif [[ "${OPERATION}" == "deploy" && "${RUN_VERIFY}" == "false" ]]; then
	log "skipping bootstrap verification"
elif [[ "${OPERATION}" == "deploy" && "${data_selected}" != "true" ]]; then
	log "skipping bootstrap verification (data stack not selected)"
fi

CURRENT_STEP="done"
log "done"