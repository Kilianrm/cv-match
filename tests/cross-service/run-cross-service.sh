#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

TEST_ENV="${TEST_ENV:-local}"
RUN_NEGATIVE="${RUN_NEGATIVE:-false}"
DB_CHECK_MODE="${DB_CHECK_MODE:-docker}"
PROFILE_POSTGRES_CONTAINER="${PROFILE_POSTGRES_CONTAINER:-profile-postgres}"

if [[ "${TEST_ENV}" != "local" && "${TEST_ENV}" != "aws-dev" ]]; then
  echo "Invalid TEST_ENV: ${TEST_ENV}. Use local or aws-dev." >&2
  exit 1
fi

run_tests() {
  local test_files=("tests/cross-service/test_e2e.py")
  if [[ "${RUN_NEGATIVE}" == "true" ]]; then
    test_files+=("tests/cross-service/test_e2e_negative.py")
  fi

  if python3 -m pytest --version >/dev/null 2>&1; then
    TEST_ENV="${TEST_ENV}" \
    DB_CHECK_MODE="${DB_CHECK_MODE}" \
    PROFILE_POSTGRES_CONTAINER="${PROFILE_POSTGRES_CONTAINER}" \
    python3 -m pytest "${test_files[@]}" -vv -s --tb=short --capture=no --color=yes
  else
    echo "pytest not found, using direct Python fallback for test_e2e.py."
    TEST_ENV="${TEST_ENV}" DB_CHECK_MODE="${DB_CHECK_MODE}" PROFILE_POSTGRES_CONTAINER="${PROFILE_POSTGRES_CONTAINER}" python3 tests/cross-service/test_e2e.py
    if [[ "${RUN_NEGATIVE}" == "true" ]]; then
      TEST_ENV="${TEST_ENV}" DB_CHECK_MODE="${DB_CHECK_MODE}" PROFILE_POSTGRES_CONTAINER="${PROFILE_POSTGRES_CONTAINER}" python3 tests/cross-service/test_e2e_negative.py
    fi
  fi
}

if [[ "${TEST_ENV}" == "local" ]]; then
  echo "Running cross-service tests in local mode..."
  echo "Expected local integration stack to already be running via ./scripts/deploy-local.sh up test integration"
  run_tests
else
  echo "Running cross-service tests in aws-dev mode..."
  echo "Expected env vars: BASE_URL and AUTH_TOKEN."
  run_tests
fi

echo ""
printf '\033[32mAll cross-service tests passed!\033[0m\n'