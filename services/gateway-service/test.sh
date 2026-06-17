#!/bin/bash

set -euo pipefail

SERVICES=(gateway-service)

cleanup() {
	echo "Stopping test containers..."
	docker compose down --remove-orphans >/dev/null
}

trap cleanup EXIT

echo "Starting required containers for test run..."
docker compose up -d --build "${SERVICES[@]}"

echo "Running gateway-service tests in Docker container..."
docker compose exec -T gateway-service env PYTHONPATH=/app pytest tests/ -vv -s --tb=short --capture=no --color=yes

echo ""
printf '\033[32mAll gateway-service tests passed!\033[0m\n'
