#!/usr/bin/env bash
set -euo pipefail

# Dev orchestration script for AWS infrastructure workflow.
#
# Actions:
# - deploy: deploy infrastructure and optionally sync frontend env
# - destroy: destroy infrastructure (optionally all resources)
# - test: run selected test suite (infra pre-deploy, smoke on deployed infra)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

ACTION=""
STACK=""
SUITE="infra"
SUITE_SPECIFIED="false"

INFRA_DEPLOY_SCRIPT="${ROOT_DIR}/infra/scripts/deploy-dev.sh"
INFRA_TEST_SCRIPT="${ROOT_DIR}/infra/scripts/test-infra.sh"
SMOKE_TEST_SCRIPT="${ROOT_DIR}/tests/integration/bootstrap-dev-db.test.sh"
SYNC_FRONTEND_SCRIPT="${ROOT_DIR}/scripts/support/sync-frontend-env-dev.sh"
BOOTSTRAP_DB_SCRIPT="${ROOT_DIR}/scripts/support/bootstrap-dev-db.sh"

print_help() {
	cat >&2 <<'EOF'
Usage: ./scripts/dev.sh --action <action> [--stack <stack>] [--suite <suite>]

Actions:
  deploy    Deploy dev infrastructure (requires --stack)
  destroy   Destroy dev infrastructure (requires --stack)
  bootstrap Bootstrap database for deployed data stack ( if exists)
  sync-frontend  Sync frontend env from deployed auth+gateway outputs
  test      Run selected test suite

Stacks:
  network   Deploy/destroy only network stack
  security  Deploy/destroy only security stack
  auth      Deploy/destroy only auth stack
  data      Deploy/destroy only data stack
  gateway   Deploy/destroy only gateway stack
  profile   Deploy/destroy only profile stack
  network,security,auth  Deploy/destroy multiple stacks (comma-separated)
  full      Deploy/destroy all stacks

Recommended incremental order (to avoid failures):
	deploy:   network -> security -> auth -> gateway -> data -> profile
	destroy:  profile -> data -> gateway -> auth -> security -> network

Suites (for 'test' action only):
	infra     Run infrastructure tests (CDK unit tests, no deployed infra required)
	smoke     Run smoke tests against deployed infra (requires --stack)

Options:
  -h, --help

Environment variables:
	APP_NAME, STAGE, AWS_REGION

Examples:
  ./scripts/dev.sh --action deploy --stack full
  ./scripts/dev.sh --action deploy --stack gateway,profile
  ./scripts/dev.sh --action destroy --stack full
  ./scripts/dev.sh --action destroy --stack gateway,profile
  ./scripts/dev.sh --action bootstrap
  ./scripts/dev.sh --action sync-frontend
  ./scripts/dev.sh --action test --suite infra
  ./scripts/dev.sh --action test --stack full --suite smoke
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--action)
			ACTION="${2:-}"
			shift 2
			;;
		--stack)
			STACK="${2:-}"
			shift 2
			;;
		--suite)
			SUITE="${2:-}"
			SUITE_SPECIFIED="true"
			shift 2
			;;
		-h|--help)
			print_help
			exit 0
			;;
		*)
			echo "error: unknown option '$1'" >&2
			print_help
			exit 1
			;;
	esac
done

if [[ "${ACTION}" == "deploy" && ! -f "${ROOT_DIR}/.env.dev" ]]; then
	if [[ -f "${ROOT_DIR}/.env.dev.example" ]]; then
		cp "${ROOT_DIR}/.env.dev.example" "${ROOT_DIR}/.env.dev"
		echo "[dev.sh] created .env.dev from .env.dev.example"
	else
		echo "error: missing ${ROOT_DIR}/.env.dev and ${ROOT_DIR}/.env.dev.example" >&2
		exit 1
	fi
fi

if [[ -f "${ROOT_DIR}/.env.dev" ]]; then
	# Load only the allowed variables from .env.dev.
	while IFS='=' read -r key value; do
		case "${key}" in
			APP_NAME)
				if [[ -z "${APP_NAME:-}" ]]; then
					APP_NAME="${value}"
				fi
				;;
			STAGE)
				if [[ -z "${STAGE:-}" ]]; then
					STAGE="${value}"
				fi
				;;
			AWS_REGION)
				if [[ -z "${AWS_REGION:-}" ]]; then
					AWS_REGION="${value}"
				fi
				;;
		esac
	done < <(grep -E '^(APP_NAME|STAGE|AWS_REGION)=' "${ROOT_DIR}/.env.dev" || true)
fi

APP_NAME="${APP_NAME:-cv-match}"
STAGE="${STAGE:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Enforce allowed input env vars for this wrapper.
unset DEPLOY_STACKS
unset USE_SHARED_SECURITY
unset PUBLIC_DB_ACCESS
unset PUBLIC_DB_ACCESS_CIDR
unset RUN_VERIFY
unset SEED_SCOPE
unset COGNITO_DOMAIN_PREFIX
unset PROFILE_SERVICE_BASE_URL
unset LOCAL_FRONTEND_BASE_URL
unset SYNC_FRONTEND_ENV
unset FRONTEND_ENV_FILE
unset OPERATION
unset DESTROY_ALL

if [[ -z "${ACTION}" ]]; then
	echo "error: --action is required" >&2
	print_help
	exit 1
fi

case "${ACTION}" in
	deploy|destroy|test|bootstrap|sync-frontend) ;;
	*)
		echo "error: invalid action '${ACTION}'. Use: deploy | destroy | bootstrap | sync-frontend | test" >&2
		exit 1
		;;
esac

if [[ "${ACTION}" != "test" && "${SUITE_SPECIFIED}" == "true" ]]; then
	echo "error: --suite can only be used with --action test" >&2
	exit 1
fi

if [[ ( "${ACTION}" == "bootstrap" || "${ACTION}" == "sync-frontend" ) && -n "${STACK}" ]]; then
	echo "error: --stack is not allowed with --action ${ACTION}" >&2
	print_help
	exit 1
fi

if [[ ( "${ACTION}" == "bootstrap" || "${ACTION}" == "sync-frontend" ) && "${SUITE_SPECIFIED}" == "true" ]]; then
	echo "error: --suite is not allowed with --action ${ACTION}" >&2
	print_help
	exit 1
fi

if [[ "${ACTION}" == "test" ]]; then
	case "${SUITE}" in
		infra|smoke) ;;
		*)
			echo "error: invalid --suite '${SUITE}'. Use: infra | smoke" >&2
			exit 1
			;;
	esac

	if [[ "${SUITE}" == "smoke" && -z "${STACK}" ]]; then
		echo "error: --stack is required with --action test --suite smoke" >&2
		print_help
		exit 1
	fi
fi

if [[ -n "${STACK}" ]]; then
	if [[ "${STACK}" == "full" ]]; then
		:
	else
		IFS=',' read -r -a requested_stacks <<< "${STACK}"
		if [[ ${#requested_stacks[@]} -eq 0 ]]; then
			echo "error: invalid --stack '${STACK}'. Use: network | security | auth | data | gateway | profile | full" >&2
			exit 1
		fi

		declare -A seen_requested=()
		normalized_stacks=()
		for raw_stack in "${requested_stacks[@]}"; do
			trimmed_stack="$(echo "${raw_stack}" | xargs)"
			case "${trimmed_stack}" in
				network|security|auth|data|gateway|profile) ;;
				*)
					echo "error: invalid --stack '${STACK}'. Use: network | security | auth | data | gateway | profile | full" >&2
					exit 1
					;;
			esac

			if [[ -z "${seen_requested[${trimmed_stack}]+x}" ]]; then
				seen_requested["${trimmed_stack}"]=1
				normalized_stacks+=("${trimmed_stack}")
			fi
		done

		STACK="$(IFS=,; echo "${normalized_stacks[*]}")"
	fi
fi

if [[ "${ACTION}" == "deploy" && -z "${STACK}" ]]; then
	echo "error: --stack is required with --action deploy" >&2
	print_help
	exit 1
fi

if [[ "${ACTION}" == "destroy" && -z "${STACK}" ]]; then
	echo "error: --stack is required with --action destroy" >&2
	print_help
	exit 1
fi

STACKS_TO_DEPLOY=""
if [[ -n "${STACK}" ]]; then
	if [[ "${STACK}" == "full" ]]; then
		STACKS_TO_DEPLOY="network,security,data,auth,profile,gateway"
	else
		STACKS_TO_DEPLOY="${STACK}"
	fi
fi

case "${ACTION}" in
	deploy)
		if [[ ! -f "${INFRA_DEPLOY_SCRIPT}" ]]; then
			echo "error: missing ${INFRA_DEPLOY_SCRIPT}" >&2
			exit 1
		fi

		if [[ -n "${STACKS_TO_DEPLOY}" ]]; then
			APP_NAME="${APP_NAME}" STAGE="${STAGE}" AWS_REGION="${AWS_REGION}" \
			DEPLOY_STACKS="${STACKS_TO_DEPLOY}" \
			bash "${INFRA_DEPLOY_SCRIPT}"
		else
			APP_NAME="${APP_NAME}" STAGE="${STAGE}" AWS_REGION="${AWS_REGION}" \
			bash "${INFRA_DEPLOY_SCRIPT}"
		fi
		;;
	destroy)
		if [[ ! -f "${INFRA_DEPLOY_SCRIPT}" ]]; then
			echo "error: missing ${INFRA_DEPLOY_SCRIPT}" >&2
			exit 1
		fi

		if [[ -n "${STACKS_TO_DEPLOY}" ]]; then
			APP_NAME="${APP_NAME}" STAGE="${STAGE}" AWS_REGION="${AWS_REGION}" DEPLOY_STACKS="${STACKS_TO_DEPLOY}" \
			bash "${INFRA_DEPLOY_SCRIPT}" --destroy
		else
			bash "${INFRA_DEPLOY_SCRIPT}" --destroy
		fi
		;;
	bootstrap)
		if [[ ! -f "${BOOTSTRAP_DB_SCRIPT}" ]]; then
			echo "error: missing ${BOOTSTRAP_DB_SCRIPT}" >&2
			exit 1
		fi
		APP_NAME="${APP_NAME}" STAGE="${STAGE}" AWS_REGION="${AWS_REGION}" \
		bash "${BOOTSTRAP_DB_SCRIPT}"
		;;
	sync-frontend)
		if [[ ! -f "${SYNC_FRONTEND_SCRIPT}" ]]; then
			echo "error: missing ${SYNC_FRONTEND_SCRIPT}" >&2
			exit 1
		fi
		APP_NAME="${APP_NAME}" STAGE="${STAGE}" AWS_REGION="${AWS_REGION}" \
		bash "${SYNC_FRONTEND_SCRIPT}"
		;;
	test)
		case "${SUITE}" in
			infra)
				if [[ ! -x "${INFRA_TEST_SCRIPT}" ]]; then
					echo "error: missing executable ${INFRA_TEST_SCRIPT}" >&2
					exit 1
				fi
				bash "${INFRA_TEST_SCRIPT}"
				;;
			smoke)
				if [[ ! -f "${SMOKE_TEST_SCRIPT}" ]]; then
					echo "error: missing ${SMOKE_TEST_SCRIPT}" >&2
					exit 1
				fi
				bash "${SMOKE_TEST_SCRIPT}"
				;;
		esac
		;;
esac
