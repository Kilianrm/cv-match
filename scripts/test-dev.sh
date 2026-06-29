#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_TEST_SCRIPT="${ROOT_DIR}/infra/scripts/test-infra.sh"

print_help() {
	echo "Usage: ./scripts/test-dev.sh"
	echo ""
	echo "Runs infrastructure dev validation by delegating to infra/scripts/test-infra.sh."
}

for arg in "$@"; do
	case "$arg" in
		-h|--help|help)
			print_help
			exit 0
			;;
		*)
			echo "Invalid argument: $arg" >&2
			print_help >&2
			exit 1
			;;
	esac
done

if [[ ! -x "${INFRA_TEST_SCRIPT}" ]]; then
	echo "[test-dev] error: missing executable ${INFRA_TEST_SCRIPT}" >&2
	exit 1
fi

echo "[test-dev] delegating to infra/scripts/test-infra.sh"
bash "${INFRA_TEST_SCRIPT}" "$@"
