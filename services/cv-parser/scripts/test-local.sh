#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_FAMILY="${SERVICE_FAMILY:-cv-parser-service}"

SERVICE_FAMILY_SLUG="$(echo "${SERVICE_FAMILY}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]/-/g')"
if [[ -z "${SERVICE_FAMILY_SLUG}" ]]; then
  echo "Invalid SERVICE_FAMILY: ${SERVICE_FAMILY}" >&2
  exit 1
fi

COMPOSE_PROJECT_NAME="${SERVICE_FAMILY_SLUG}-test"

COMPOSE_CMD=(
  docker compose
  -p "${COMPOSE_PROJECT_NAME}"
  --project-directory "$SCRIPT_DIR"
  -f "$SCRIPT_DIR/docker-compose.yml"
  -f "$SCRIPT_DIR/docker-compose.override.yml"
)

echo "Running cv-parser-service tests in Docker container (project: ${COMPOSE_PROJECT_NAME})..."
"${COMPOSE_CMD[@]}" exec cv-parser-service sh -lc '
  env PYTHONPATH=/app pytest tests/ -vv -s --tb=short --capture=no --color=yes \
    --cov=src --cov-report=term-missing --cov-report=xml:/app/coverage.xml
'

echo ""
printf '\033[32mAll cv-parser-service tests passed!\033[0m\n'
