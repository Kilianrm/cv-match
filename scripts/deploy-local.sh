#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="${ACTION:-up}"
DEPLOY_MODE="${DEPLOY_MODE:-test}"
DEPLOY_SCOPE="${DEPLOY_SCOPE:-services}"
REMOVE_VOLUMES="${REMOVE_VOLUMES:-false}"
PRE_CLEAN_BEFORE_UP="${PRE_CLEAN_BEFORE_UP:-true}"

compose_cmd() {
	if docker compose version >/dev/null 2>&1; then
		echo "docker compose"
	elif command -v docker-compose >/dev/null 2>&1; then
		echo "docker-compose"
	else
		echo "Docker Compose is required (docker compose or docker-compose)." >&2
		exit 1
	fi
}

cd "${ROOT_DIR}"

COMPOSE_CMD="$(compose_cmd)"

parse_positional_args() {
	for arg in "$@"; do
		case "$arg" in
			up|down)
				ACTION="$arg"
				;;
			runtime|test)
				DEPLOY_MODE="$arg"
				;;
			services|cross-service)
				DEPLOY_SCOPE="$arg"
				;;
			-h|--help|help)
				echo "Usage: ./scripts/deploy-local.sh [up|down] [runtime|test] [services|cross-service]"
				echo "Examples:"
				echo "  ./scripts/deploy-local.sh"
				echo "  ./scripts/deploy-local.sh up test services"
				echo "  ./scripts/deploy-local.sh up test cross-service"
				echo "  ./scripts/deploy-local.sh down"
				exit 0
				;;
			*)
				echo "Invalid argument: $arg" >&2
				echo "Usage: ./scripts/deploy-local.sh [up|down] [runtime|test] [services|cross-service]" >&2
				exit 1
				;;
		esac
	done
}

parse_positional_args "$@"

if [[ "${ACTION}" != "up" && "${ACTION}" != "down" ]]; then
	echo "Invalid ACTION: ${ACTION}. Use up or down." >&2
	exit 1
fi

if [[ "${DEPLOY_MODE}" != "runtime" && "${DEPLOY_MODE}" != "test" ]]; then
	echo "Invalid DEPLOY_MODE: ${DEPLOY_MODE}. Use runtime or test." >&2
	exit 1
fi

if [[ "${DEPLOY_SCOPE}" != "services" && "${DEPLOY_SCOPE}" != "cross-service" ]]; then
	echo "Invalid DEPLOY_SCOPE: ${DEPLOY_SCOPE}. Use services or cross-service." >&2
	exit 1
fi

down_cross_services() {
	cross_services_project_name="${COMPOSE_PROJECT_NAME:-cv-match-cross-service}"
	compose_args=(-p "${cross_services_project_name}" -f "${ROOT_DIR}/docker-compose.yml")
	echo "[deploy-local] stopping cross-service stack"
	if [[ "${REMOVE_VOLUMES}" == "true" ]]; then
		${COMPOSE_CMD} "${compose_args[@]}" down --remove-orphans --volumes
	else
		${COMPOSE_CMD} "${compose_args[@]}" down --remove-orphans
	fi
}

down_services() {
	for service_dir in "${ROOT_DIR}"/services/*; do
		[[ -d "${service_dir}" ]] || continue
		service_name="$(basename "${service_dir}")"
		service_deploy_script="${service_dir}/scripts/deploy-local.sh"
		if [[ ! -x "${service_deploy_script}" ]]; then
			echo "[deploy-local] error: ${service_name} is missing executable scripts/deploy-local.sh" >&2
			exit 1
		fi
		echo "[deploy-local] delegating ${service_name} -> scripts/deploy-local.sh (down ${DEPLOY_MODE})"
		(
			cd "${service_dir}"
			ACTION=down \
			DEPLOY_MODE="${DEPLOY_MODE}" \
			REMOVE_VOLUMES="${REMOVE_VOLUMES}" \
			COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-}" \
			bash ./scripts/deploy-local.sh down "${DEPLOY_MODE}"
		)
	done
}

if [[ "${ACTION}" == "down" ]]; then
	down_services
	down_cross_services
elif [[ "${DEPLOY_SCOPE}" == "services" ]]; then
	for service_dir in "${ROOT_DIR}"/services/*; do
		if [[ ! -d "${service_dir}" ]]; then
			continue
		fi

		service_name="$(basename "${service_dir}")"
		service_deploy_script="${service_dir}/scripts/deploy-local.sh"

		if [[ -x "${service_deploy_script}" ]]; then
			echo "[deploy-local] delegating ${service_name} -> scripts/deploy-local.sh (${ACTION} ${DEPLOY_MODE})"
			(
				cd "${service_dir}"
				ACTION="${ACTION}" \
				DEPLOY_MODE="${DEPLOY_MODE}" \
				REMOVE_VOLUMES="${REMOVE_VOLUMES}" \
				COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-}" \
				bash ./scripts/deploy-local.sh "${ACTION}" "${DEPLOY_MODE}"
			)
		else
			echo "[deploy-local] error: ${service_name} is missing executable scripts/deploy-local.sh" >&2
			exit 1
		fi
	done
else
	cross_services_project_name="${COMPOSE_PROJECT_NAME:-cv-match-cross-service}"
	compose_args=(-p "${cross_services_project_name}" -f "${ROOT_DIR}/docker-compose.yml")

	if [[ "${ACTION}" == "up" ]]; then
		if [[ "${PRE_CLEAN_BEFORE_UP}" == "true" ]]; then
			echo "[deploy-local] pre-cleaning cross-service stack"
			if [[ "${REMOVE_VOLUMES}" == "true" ]]; then
				${COMPOSE_CMD} "${compose_args[@]}" down --remove-orphans --volumes >/dev/null 2>&1 || true
			else
				${COMPOSE_CMD} "${compose_args[@]}" down --remove-orphans >/dev/null 2>&1 || true
			fi

			echo "[deploy-local] pre-cleaning service-local stacks before cross-service deploy"
			for service_dir in "${ROOT_DIR}"/services/*; do
				if [[ ! -d "${service_dir}" ]]; then
					continue
				fi

				service_name="$(basename "${service_dir}")"
				service_deploy_script="${service_dir}/scripts/deploy-local.sh"
				if [[ ! -x "${service_deploy_script}" ]]; then
					echo "[deploy-local] error: ${service_name} is missing executable scripts/deploy-local.sh" >&2
					exit 1
				fi

				(
					cd "${service_dir}"
					REMOVE_VOLUMES="${REMOVE_VOLUMES}" bash ./scripts/deploy-local.sh down test >/dev/null 2>&1 || true
				)
			done
		fi

		echo "[deploy-local] deploying cross-service stack"
		${COMPOSE_CMD} "${compose_args[@]}" up -d --build
	else
		echo "[deploy-local] stopping cross-service stack"
		if [[ "${REMOVE_VOLUMES}" == "true" ]]; then
			${COMPOSE_CMD} "${compose_args[@]}" down --remove-orphans --volumes
		else
			${COMPOSE_CMD} "${compose_args[@]}" down --remove-orphans
		fi
	fi
fi

