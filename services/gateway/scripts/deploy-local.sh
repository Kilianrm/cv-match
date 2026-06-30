#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="${ACTION:-up}"
REMOVE_VOLUMES="${REMOVE_VOLUMES:-false}"
DEPLOY_MODE="${DEPLOY_MODE:-runtime}"
SERVICE_FAMILY="${SERVICE_FAMILY:-gateway-service}"

down_all_family_projects() {
  local extra_args=(--remove-orphans)
  if [[ "${REMOVE_VOLUMES}" == "true" ]]; then
    extra_args+=(--volumes)
  fi

  docker compose \
    -p "${SERVICE_FAMILY_SLUG}-runtime" \
    --project-directory "$SCRIPT_DIR" \
    -f "$SCRIPT_DIR/docker-compose.yml" \
    down "${extra_args[@]}" >/dev/null 2>&1 || true

  docker compose \
    -p "${SERVICE_FAMILY_SLUG}-test" \
    --project-directory "$SCRIPT_DIR" \
    -f "$SCRIPT_DIR/docker-compose.yml" \
    -f "$SCRIPT_DIR/docker-compose.override.yml" \
    down "${extra_args[@]}" >/dev/null 2>&1 || true
}

parse_positional_args() {
  for arg in "$@"; do
    case "$arg" in
      up|down)
        ACTION="$arg"
        ;;
      runtime|test)
        DEPLOY_MODE="$arg"
        ;;
      -h|--help|help)
        echo "Usage: ./scripts/deploy-local.sh [up|down] [runtime|test]"
        echo "Examples:"
        echo "  ./scripts/deploy-local.sh"
        echo "  ./scripts/deploy-local.sh up test"
        echo "  ./scripts/deploy-local.sh down runtime"
        echo "  ACTION=down DEPLOY_MODE=test ./scripts/deploy-local.sh"
        exit 0
        ;;
      *)
        echo "Invalid argument: $arg" >&2
        echo "Usage: ./scripts/deploy-local.sh [up|down] [runtime|test]" >&2
        exit 1
        ;;
    esac
  done
}

parse_positional_args "$@"

SERVICE_FAMILY_SLUG="$(echo "${SERVICE_FAMILY}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]/-/g')"
if [[ -z "${SERVICE_FAMILY_SLUG}" ]]; then
  echo "Invalid SERVICE_FAMILY: ${SERVICE_FAMILY}" >&2
  exit 1
fi

if [[ "${DEPLOY_MODE}" == "runtime" ]]; then
  DEFAULT_PROJECT_NAME="${SERVICE_FAMILY_SLUG}-runtime"
elif [[ "${DEPLOY_MODE}" == "test" ]]; then
  DEFAULT_PROJECT_NAME="${SERVICE_FAMILY_SLUG}-test"
else
  echo "Invalid DEPLOY_MODE: ${DEPLOY_MODE}. Use runtime or test." >&2
  exit 1
fi

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-${DEFAULT_PROJECT_NAME}}"

COMPOSE_BASE=(
  docker compose
  -p "${COMPOSE_PROJECT_NAME}"
  --project-directory "$SCRIPT_DIR"
  -f "$SCRIPT_DIR/docker-compose.yml"
)

COMPOSE_TEST=(
  docker compose
  -p "${COMPOSE_PROJECT_NAME}"
  --project-directory "$SCRIPT_DIR"
  -f "$SCRIPT_DIR/docker-compose.yml"
  -f "$SCRIPT_DIR/docker-compose.override.yml"
)

if [[ "${DEPLOY_MODE}" == "runtime" ]]; then
  COMPOSE_CMD=("${COMPOSE_BASE[@]}")
else
  COMPOSE_CMD=("${COMPOSE_TEST[@]}")
fi

if [[ "${ACTION}" == "up" ]]; then
  down_all_family_projects
  echo "Deploying gateway-service local stack (mode: ${DEPLOY_MODE}, project: ${COMPOSE_PROJECT_NAME})..."
  "${COMPOSE_CMD[@]}" up -d --build
  echo "gateway-service URL: http://localhost:8000"
elif [[ "${ACTION}" == "down" ]]; then
  echo "Stopping gateway-service local stack (mode: ${DEPLOY_MODE}, project: ${COMPOSE_PROJECT_NAME})..."
  down_all_family_projects
else
  echo "Invalid ACTION: ${ACTION}. Use up or down." >&2
  exit 1
fi
