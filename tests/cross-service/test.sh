#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

SERVICES=(gateway-service profile-service postgres localstack)

cleanup() {
    echo "Stopping test containers..."
  docker compose down --remove-orphans -v >/dev/null
}

trap cleanup EXIT

echo "Starting required containers for test run..."
docker compose down --remove-orphans -v >/dev/null 2>&1 || true
docker compose up -d --build "${SERVICES[@]}"

# Cross-service tests run on host because they orchestrate multiple containers
# and validate public gateway behavior end-to-end.
echo "Running cross-service tests..."
if python3 -m pytest --version >/dev/null 2>&1; then
  python3 -m pytest tests/cross-service/test_e2e.py -vv -s --tb=short --capture=no --color=yes
else
  echo "pytest not found, using direct Python fallback."
  python3 tests/cross-service/test_e2e.py
fi

echo ""
printf '\033[32mAll cross-service tests passed!\033[0m\n'
