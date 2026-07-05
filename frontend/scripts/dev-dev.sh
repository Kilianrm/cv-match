#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

ENV_DEV_FILE="${ROOT_DIR}/.env.dev"
ENV_LOCAL_FILE="${ROOT_DIR}/.env.local"
ENV_LOCAL_BACKUP_FILE="${ROOT_DIR}/.env.local.copilot.bak"

if [[ ! -f "${ENV_DEV_FILE}" ]]; then
  echo "error: ${ENV_DEV_FILE} not found" >&2
  exit 1
fi

restore_env_local() {
  if [[ -f "${ENV_LOCAL_BACKUP_FILE}" ]]; then
    mv "${ENV_LOCAL_BACKUP_FILE}" "${ENV_LOCAL_FILE}"
  fi
}

trap restore_env_local EXIT

if [[ -f "${ENV_LOCAL_FILE}" ]]; then
  mv "${ENV_LOCAL_FILE}" "${ENV_LOCAL_BACKUP_FILE}"
fi

echo "[dev:dev] env source: ${ENV_DEV_FILE}"
if [[ -f "${ENV_LOCAL_BACKUP_FILE}" ]]; then
  echo "[dev:dev] .env.local temporarily disabled"
else
  echo "[dev:dev] no .env.local found"
fi

effective_gateway_url="$(grep -E '^API_GATEWAY_BASE_URL=' "${ENV_DEV_FILE}" | sed 's/^API_GATEWAY_BASE_URL=//')"
echo "[dev:dev] API_GATEWAY_BASE_URL=${effective_gateway_url}"

# Load .env.dev via dotenv parsing and run Next.js dev server.
# With .env.local temporarily moved away, Next won't override these values.
exec dotenv -e "${ENV_DEV_FILE}" -- next dev
