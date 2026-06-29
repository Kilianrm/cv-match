#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="${ACTION:-up}"
DEPLOY_MODE="${DEPLOY_MODE:-test}"
DEPLOY_SCOPE="${DEPLOY_SCOPE:-services}"
REMOVE_VOLUMES="${REMOVE_VOLUMES:-false}"
PRE_CLEAN_BEFORE_UP="${PRE_CLEAN_BEFORE_UP:-true}"
SKIP_PORT_CHECK="${SKIP_PORT_CHECK:-false}"
AUTO_FREE_PORTS="${AUTO_FREE_PORTS:-true}"
REQUIRED_LOCAL_PORTS="${REQUIRED_LOCAL_PORTS:-8000,8080,5432,4566}"

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

validate_bool() {
	local name="$1"
	local value="$2"
	if [[ "${value}" != "true" && "${value}" != "false" ]]; then
		echo "Invalid ${name}: ${value}. Use true or false." >&2
		exit 1
	fi
}

validate_bool "REMOVE_VOLUMES" "${REMOVE_VOLUMES}"
validate_bool "PRE_CLEAN_BEFORE_UP" "${PRE_CLEAN_BEFORE_UP}"
validate_bool "SKIP_PORT_CHECK" "${SKIP_PORT_CHECK}"
validate_bool "AUTO_FREE_PORTS" "${AUTO_FREE_PORTS}"

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

is_port_busy() {
	local port="$1"

	if docker ps --format '{{.Ports}}' | grep -Eq "(^|[[:space:]],)[^,]*:${port}->"; then
		return 0
	fi

	if command -v ss >/dev/null 2>&1; then
		if ss -ltnH "sport = :${port}" 2>/dev/null | grep -q .; then
			return 0
		fi
	elif command -v lsof >/dev/null 2>&1; then
		if lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
			return 0
		fi
	fi

	return 1
}

report_port_owner() {
	local port="$1"
	local docker_matches
	docker_matches="$(docker ps --format '{{.Names}}\t{{.Ports}}' | grep -E "(^|[[:space:]],)[^,]*:${port}->" || true)"

	if [[ -n "${docker_matches}" ]]; then
		echo "[deploy-local] port ${port} is published by running container(s):"
		echo "${docker_matches}" | sed 's/^/  - /'
	fi

	if command -v ss >/dev/null 2>&1; then
		local listeners
		listeners="$(ss -ltnH "sport = :${port}" 2>/dev/null || true)"
		if [[ -n "${listeners}" ]]; then
			echo "[deploy-local] host listener(s) on port ${port}:"
			echo "${listeners}" | sed 's/^/  - /'
		fi
	elif command -v lsof >/dev/null 2>&1; then
		local processes
		processes="$(lsof -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
		if [[ -n "${processes}" ]]; then
			echo "[deploy-local] host process(es) on port ${port}:"
			echo "${processes}" | sed 's/^/  - /'
		fi
	fi
}

free_port() {
	local port="$1"
	local container_ids
	local did_anything="false"
	container_ids="$(docker ps --format '{{.ID}}\t{{.Ports}}' | awk -F '\t' -v p="${port}" '$2 ~ (":" p "->") {print $1}')"

	if [[ -n "${container_ids}" ]]; then
		echo "[deploy-local] freeing port ${port}: removing container(s) ${container_ids}"
		docker rm -f ${container_ids} >/dev/null || true
		did_anything="true"
	fi

	if command -v lsof >/dev/null 2>&1; then
		local pids
		pids="$(lsof -t -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null | sort -u | tr '\n' ' ' || true)"
		if [[ -n "${pids}" ]]; then
			echo "[deploy-local] freeing port ${port}: terminating process(es) ${pids}"
			kill ${pids} >/dev/null 2>&1 || true
			did_anything="true"
		fi
	fi

	if [[ "${did_anything}" == "false" ]] && command -v ss >/dev/null 2>&1; then
		local ss_pids
		ss_pids="$(ss -ltnp "sport = :${port}" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u | tr '\n' ' ' || true)"
		if [[ -n "${ss_pids}" ]]; then
			echo "[deploy-local] freeing port ${port}: terminating PID(s) from ss ${ss_pids}"
			kill ${ss_pids} >/dev/null 2>&1 || true
			did_anything="true"
		fi
	fi

	if [[ "${did_anything}" == "false" ]] && command -v fuser >/dev/null 2>&1; then
		echo "[deploy-local] freeing port ${port}: killing listeners with fuser"
		fuser -k "${port}/tcp" >/dev/null 2>&1 || true
		did_anything="true"
	fi

	if [[ "${did_anything}" == "false" ]]; then
		echo "[deploy-local] unable to auto-free port ${port} (no matching container and no process tool access)" >&2
	fi
}

remove_all_running_containers() {
	local running_ids
	running_ids="$(docker ps -q | tr '\n' ' ')"

	if [[ -z "${running_ids// }" ]]; then
		echo "[deploy-local] no running containers to remove"
		return
	fi

	echo "[deploy-local] force cleanup: removing all running containers"
	docker rm -f ${running_ids} >/dev/null || true
}

preflight_check_ports() {
	if [[ "${ACTION}" != "up" || "${SKIP_PORT_CHECK}" == "true" ]]; then
		return
	fi

	IFS=',' read -r -a ports <<< "${REQUIRED_LOCAL_PORTS}"
	local unresolved=0

	for port in "${ports[@]}"; do
		port="$(echo "${port}" | xargs)"
		if [[ -z "${port}" || ! "${port}" =~ ^[0-9]+$ ]]; then
			continue
		fi

		if is_port_busy "${port}"; then
			report_port_owner "${port}"
			if [[ "${AUTO_FREE_PORTS}" == "true" ]]; then
				free_port "${port}"
				if is_port_busy "${port}"; then
					unresolved=1
					echo "[deploy-local] could not free port ${port}" >&2
				fi
			else
				unresolved=1
			fi
		fi
	done

	if [[ "${unresolved}" -eq 1 ]]; then
		echo "[deploy-local] unresolved port conflicts remain; force-removing all running containers and retrying"
		remove_all_running_containers
		unresolved=0

		for port in "${ports[@]}"; do
			port="$(echo "${port}" | xargs)"
			if [[ -z "${port}" || ! "${port}" =~ ^[0-9]+$ ]]; then
				continue
			fi

			if is_port_busy "${port}"; then
				unresolved=1
				report_port_owner "${port}"
			fi
		done

		if [[ "${unresolved}" -eq 1 ]]; then
			echo "[deploy-local] port preflight failed even after removing all running containers." >&2
			echo "[deploy-local] rerun with SKIP_PORT_CHECK=true to bypass (not recommended)." >&2
			exit 1
		fi
	fi
}

preflight_check_ports

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

