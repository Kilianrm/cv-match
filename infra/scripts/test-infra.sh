#!/usr/bin/env bash
set -euo pipefail

INFRA_SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "${INFRA_SCRIPTS_DIR}/.." && pwd)"

parse_positional_args() {
	for arg in "$@"; do
		case "$arg" in
			-h|--help|help)
				echo "Usage: ./infra/scripts/test-infra.sh"
				echo ""
				echo "Runs CDK unit tests for infrastructure."
				exit 0
				;;
			*)
				echo "Invalid argument: $arg" >&2
				echo "Usage: ./infra/scripts/test-infra.sh" >&2
				exit 1
				;;
		esac
	done
}

parse_positional_args "$@"

echo "================================================"
echo "Running CDK unit tests..."
echo "================================================"
cd "${INFRA_DIR}/cdk"
npm test -- --runInBand

echo ""
echo "================================================"
echo "Infrastructure tests completed successfully"
echo "================================================"
