#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_CMD=(
	docker compose
	-p cv-match
	--project-directory "$SCRIPT_DIR"
	-f "$SCRIPT_DIR/docker-compose.yml"
	-f "$SCRIPT_DIR/docker-compose.override.yml"
)

REQUIRED_SERVICES=(postgres localstack)
STARTED_SERVICES=()

cleanup() {
	if [[ ${#STARTED_SERVICES[@]} -gt 0 ]]; then
		echo "Stopping services started by this test run..."
		"${COMPOSE_CMD[@]}" stop "${STARTED_SERVICES[@]}" >/dev/null || true
	fi
}

trap cleanup EXIT

echo "Ensuring required containers are running..."
for service in "${REQUIRED_SERVICES[@]}"; do
	if [[ -z "$("${COMPOSE_CMD[@]}" ps -q "$service")" ]]; then
		STARTED_SERVICES+=("$service")
	fi
done

if [[ ${#STARTED_SERVICES[@]} -gt 0 ]]; then
	echo "Starting missing services: ${STARTED_SERVICES[*]}"
	"${COMPOSE_CMD[@]}" up -d --build "${STARTED_SERVICES[@]}"
fi

echo "Running profile-service tests in Docker container..."
"${COMPOSE_CMD[@]}" run --build --rm --no-deps -v "${SCRIPT_DIR}:/app" profile-service sh -lc '
	pytest tests/ -vv -s --tb=short --capture=no --color=yes \
		--cov=src --cov-report=term-missing --cov-report=xml:/app/coverage.xml
'

echo ""
printf '\033[32mAll profile-service tests passed!\033[0m\n'
