#!/usr/bin/env bash
set -euo pipefail

# Local orchestration — minimal, consistent with ./dev CLI
# Called by ./dev; can also be used directly for testing

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

# ─── Arguments ─────────────────────────────────────────────────────────────────

ACTION=""
STACK=""
MODE=""
SUITE="all"
SKIP_FRONTEND=false

print_help() {
	cat >&2 <<'EOF'
Usage: ./scripts/local.sh --action <action> --stack <stack> [--suite <suite>] [--skip-frontend]

Actions:
  up       Bring up services (runtime mode)
  down     Tear down services
  test     Run tests (self-contained: up ? test ? down)

Stacks:
  gateway               Only gateway service
  profile               Only profile service
  full                  All services via root docker-compose.yml
  gateway,profile       Multiple services (comma-separated)

Options:
  --skip-frontend       Exclude frontend from --stack full (for runtime only)

Suites (for 'test' action only):
  unit          Service-level unit tests (required for individual/multiple services)
  integration   Cross-service integration tests (required for --stack full)
  e2e           End-to-end tests (required for --stack full)

Examples:
  ./scripts/local.sh --action up --stack gateway
  ./scripts/local.sh --action up --stack gateway,profile
  ./scripts/local.sh --action up --stack full
  ./scripts/local.sh --action up --stack full --skip-frontend
  ./scripts/local.sh --action down --stack profile
  ./scripts/local.sh --action test --stack gateway --suite unit
  ./scripts/local.sh --action test --stack gateway,profile --suite unit
  ./scripts/local.sh --action test --stack full --suite integration
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
			shift 2
			;;
		--skip-frontend)
			SKIP_FRONTEND=true
			shift
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

# Validate required arguments
if [[ -z "${ACTION}" ]]; then
	echo "error: --action is required" >&2
	print_help
	exit 1
fi

if [[ -z "${STACK}" ]]; then
	echo "error: --stack is required" >&2
	print_help
	exit 1
fi

# Validate ACTION
case "${ACTION}" in
	up|down|test) ;;
	*)
		echo "error: invalid action '${ACTION}'. Use: up | down | test" >&2
		exit 1
		;;
esac

# Set MODE based on ACTION
case "${ACTION}" in
	up)     MODE="runtime" ;;
	down)   MODE="test" ;;
	test)   MODE="test" ;;
esac

# Validate STACK
case "${STACK}" in
	gateway|profile|full) ;;
	*)
		# Check if it's comma-separated list of valid stacks
		valid_stack=true
		IFS=',' read -ra stacks <<< "${STACK}"
		for s in "${stacks[@]}"; do
			s="$(echo "$s" | xargs)"  # trim whitespace
			if [[ "$s" != "gateway" && "$s" != "profile" ]]; then
				valid_stack=false
				break
			fi
		done
		if [[ "${valid_stack}" != "true" ]]; then
			echo "error: invalid stack '${STACK}'. Use: gateway | profile | full | gateway,profile | etc." >&2
			exit 1
		fi
		;;
esac

# Validate --suite is only used with test action
if [[ -n "${SUITE}" && "${SUITE}" != "all" && "${ACTION}" != "test" ]]; then
	echo "error: --suite can only be used with --action test" >&2
	exit 1
fi

# Validate --suite requirements based on stack type
if [[ "${ACTION}" == "test" ]]; then
	if [[ "${STACK}" == "full" ]]; then
		# Full stack: must use integration or e2e (not unit)
		if [[ "${SUITE}" == "unit" || "${SUITE}" == "all" ]]; then
			echo "error: --action test --stack full requires --suite integration or e2e" >&2
			exit 1
		fi
	else
		# Single service or multiple services: must use 'unit' suite
		if [[ "${SUITE}" != "unit" ]]; then
			echo "error: --action test --stack ${STACK} requires --suite unit" >&2
			exit 1
		fi
	fi
fi

# ─── Helpers ───────────────────────────────────────────────────────────────────

compose_cmd() {
	if docker compose version >/dev/null 2>&1; then
		echo "docker compose"
	elif command -v docker-compose >/dev/null 2>&1; then
		echo "docker-compose"
	else
		echo "Docker Compose is required" >&2
		exit 1
	fi
}

is_port_busy() {
	local port="$1"
	if docker ps --format '{{.Ports}}' 2>/dev/null | grep -Eq "(^|[[:space:]],)[^,]*:${port}->"; then
		return 0
	fi
	if ss -ltnH "sport = :${port}" 2>/dev/null | grep -q .; then
		return 0
	fi
	return 1
}

free_port() {
	local port="$1"
	echo "[local] freeing port ${port}"
	docker ps --format '{{.ID}}\t{{.Ports}}' 2>/dev/null | awk -F '\t' -v p="${port}" '$2 ~ (":" p "->") {print $1}' | xargs -r docker rm -f >/dev/null 2>&1 || true
	if command -v lsof >/dev/null 2>&1; then
		lsof -t -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null | xargs -r kill -9 >/dev/null 2>&1 || true
	fi
}

ensure_ports_free() {
	local ports=(8000 8080 5432 4566)
	if [[ "${MODE}" == "runtime" ]]; then
		ports+=(3000)
	fi
	for port in "${ports[@]}"; do
		if is_port_busy "${port}"; then
			free_port "${port}"
			if is_port_busy "${port}"; then
				echo "error: could not free port ${port}" >&2
				exit 1
			fi
		fi
	done
}

COMPOSE_CMD="$(compose_cmd)"

# ─── Service helpers ───────────────────────────────────────────────────────────

up_services() {
	local selected_stacks="$1"  # comma-separated or single service name
	ensure_ports_free
	
	for service_dir in "${ROOT_DIR}"/services/*; do
		[[ -d "${service_dir}" ]] || continue
		local service_name="$(basename "${service_dir}")"
		
		# Check if this service should be deployed
		local should_deploy=false
		IFS=',' read -ra stacks_array <<< "${selected_stacks}"
		for s in "${stacks_array[@]}"; do
			s="$(echo "$s" | xargs)"  # trim whitespace
			if [[ "${s}" == "${service_name}" ]]; then
				should_deploy=true
				break
			fi
		done
		if [[ "${should_deploy}" != "true" ]]; then
			continue
		fi
		
		local deploy_script="${service_dir}/scripts/deploy-local.sh"
		if [[ ! -x "${deploy_script}" ]]; then
			echo "error: ${service_name} missing scripts/deploy-local.sh" >&2
			exit 1
		fi
		
		echo "[local] up ${service_name} (${MODE})"
		(
			cd "${service_dir}"
			bash ./scripts/deploy-local.sh up "${MODE}"
		)
	done
}

down_services() {
	local selected_stacks="$1"  # comma-separated or single service name
	
	for service_dir in "${ROOT_DIR}"/services/*; do
		[[ -d "${service_dir}" ]] || continue
		local service_name="$(basename "${service_dir}")"
		
		# Check if this service should be torn down
		local should_down=false
		IFS=',' read -ra stacks_array <<< "${selected_stacks}"
		for s in "${stacks_array[@]}"; do
			s="$(echo "$s" | xargs)"  # trim whitespace
			if [[ "${s}" == "${service_name}" ]]; then
				should_down=true
				break
			fi
		done
		if [[ "${should_down}" != "true" ]]; then
			continue
		fi
		
		local deploy_script="${service_dir}/scripts/deploy-local.sh"
		if [[ ! -x "${deploy_script}" ]]; then
			echo "error: ${service_name} missing scripts/deploy-local.sh" >&2
			exit 1
		fi
		
		echo "[local] down ${service_name}"
		(
			cd "${service_dir}"
			bash ./scripts/deploy-local.sh down "${MODE}"
		)
	done
}

up_cross_service() {
	ensure_ports_free
	
	# Pre-clean
	echo "[local] pre-cleaning cross-service stack"
	${COMPOSE_CMD} -p cv-match-cross-service -f "${ROOT_DIR}/docker-compose.yml" down --remove-orphans >/dev/null 2>&1 || true
	
	# Pre-clean individual services
	for service_dir in "${ROOT_DIR}"/services/*; do
		[[ -d "${service_dir}" ]] || continue
		(cd "${service_dir}" && bash ./scripts/deploy-local.sh down test >/dev/null 2>&1 || true)
	done
	
	# Deploy cross-service
	echo "[local] up full stack (${MODE})"
	if [[ "${MODE}" == "runtime" ]] && [[ "${SKIP_FRONTEND}" != "true" ]]; then
		# Full stack with frontend
		${COMPOSE_CMD} -p cv-match-cross-service -f "${ROOT_DIR}/docker-compose.yml" up -d --build
	else
		# Exclude frontend (either test mode or --skip-frontend flag)
		${COMPOSE_CMD} -p cv-match-cross-service -f "${ROOT_DIR}/docker-compose.yml" up -d --build gateway profile postgres localstack
	fi
}

down_cross_service() {
	echo "[local] down full stack"
	${COMPOSE_CMD} -p cv-match-cross-service -f "${ROOT_DIR}/docker-compose.yml" down --remove-orphans
}

test_services() {
	local selected_stacks="$1"  # comma-separated or single service name
	
	for service_dir in "${ROOT_DIR}"/services/*; do
		[[ -d "${service_dir}" ]] || continue
		local service_name="$(basename "${service_dir}")"
		
		# Check if this service should be tested
		local should_test=false
		IFS=',' read -ra stacks_array <<< "${selected_stacks}"
		for s in "${stacks_array[@]}"; do
			s="$(echo "$s" | xargs)"  # trim whitespace
			if [[ "${s}" == "${service_name}" ]]; then
				should_test=true
				break
			fi
		done
		if [[ "${should_test}" != "true" ]]; then
			continue
		fi
		
		local test_script="${service_dir}/scripts/test-local.sh"
		if [[ ! -x "${test_script}" ]]; then
			echo "error: ${service_name} missing scripts/test-local.sh" >&2
			exit 1
		fi
		
		echo "[local] test ${service_name}"
		(cd "${service_dir}" && bash ./scripts/test-local.sh)
	done
}

test_cross_service() {
	echo "[local] test full stack (e2e)"
	if python3 -m pytest --version >/dev/null 2>&1; then
		python3 -m pytest "${ROOT_DIR}/tests/cross-service" -vv -s --tb=short --capture=no --color=yes
	else
		python3 "${ROOT_DIR}/tests/cross-service/test_e2e.py"
		python3 "${ROOT_DIR}/tests/cross-service/test_e2e_negative.py"
	fi
}

# ─── Dispatch ──────────────────────────────────────────────────────────────────

case "${ACTION}" in
	up)
		if [[ "${STACK}" == "full" ]]; then
			up_cross_service
		else
			up_services "${STACK}"
		fi
		;;
	down)
		if [[ "${STACK}" == "full" ]]; then
			down_cross_service
		else
			down_services "${STACK}"
		fi
		;;
	test)
		# Test is self-contained: up ? run tests ? down (with cleanup on failure)
		(
			trap 'if [[ "${STACK}" == "full" ]]; then down_cross_service; else down_services "${STACK}"; fi' EXIT
			if [[ "${STACK}" == "full" ]]; then
				up_cross_service
			else
				up_services "${STACK}"
			fi
			if [[ "${STACK}" == "full" ]]; then
				test_cross_service
			else
				test_services "${STACK}"
			fi
		)
		;;
esac

echo "[local] done"
