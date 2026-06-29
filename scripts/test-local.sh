#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_SCOPE="${TEST_SCOPE:-services}"

parse_positional_args() {
	for arg in "$@"; do
		case "$arg" in
			services|cross-service)
				TEST_SCOPE="$arg"
				;;
			-h|--help|help)
				echo "Usage: ./scripts/test-local.sh [services|cross-service]"
				echo "Examples:"
				echo "  ./scripts/test-local.sh"
				echo "  ./scripts/test-local.sh services"
				echo "  ./scripts/test-local.sh cross-service"
				exit 0
				;;
			*)
				echo "Invalid argument: $arg" >&2
				echo "Usage: ./scripts/test-local.sh [services|cross-service]" >&2
				exit 1
				;;
		esac
	done
}

parse_positional_args "$@"

if [[ "${TEST_SCOPE}" != "services" && "${TEST_SCOPE}" != "cross-service" ]]; then
	echo "Invalid TEST_SCOPE: ${TEST_SCOPE}. Use services or cross-service." >&2
	exit 1
fi

cd "${ROOT_DIR}"

run_service_local_tests() {
	for service_dir in "${ROOT_DIR}"/services/*; do
		if [[ ! -d "${service_dir}" ]]; then
			continue
		fi

		service_name="$(basename "${service_dir}")"
		service_test_script="${service_dir}/scripts/test-local.sh"

		if [[ ! -x "${service_test_script}" ]]; then
			echo "[test-local] error: ${service_name} is missing executable scripts/test-local.sh" >&2
			exit 1
		fi

		echo "[test-local] delegating ${service_name} -> scripts/test-local.sh"
		(
			cd "${service_dir}"
			bash ./scripts/test-local.sh
		)
	done
}

run_cross_service_tests() {
	echo "[test-local] running cross-service suite"
	if python3 -m pytest --version >/dev/null 2>&1; then
		TEST_ENV=local DB_CHECK_MODE=docker PROFILE_POSTGRES_CONTAINER="${PROFILE_POSTGRES_CONTAINER:-profile-postgres}" \
			python3 -m pytest "${ROOT_DIR}/tests/cross-service" -vv -s --tb=short --capture=no --color=yes
	else
		echo "[test-local] pytest not found, using direct Python execution"
		TEST_ENV=local DB_CHECK_MODE=docker PROFILE_POSTGRES_CONTAINER="${PROFILE_POSTGRES_CONTAINER:-profile-postgres}" \
			python3 "${ROOT_DIR}/tests/cross-service/test_e2e.py"
		TEST_ENV=local DB_CHECK_MODE=docker PROFILE_POSTGRES_CONTAINER="${PROFILE_POSTGRES_CONTAINER:-profile-postgres}" \
			python3 "${ROOT_DIR}/tests/cross-service/test_e2e_negative.py"
	fi
}

if [[ "${TEST_SCOPE}" == "services" ]]; then
	run_service_local_tests
else
	run_cross_service_tests
fi

echo "[test-local] done"
