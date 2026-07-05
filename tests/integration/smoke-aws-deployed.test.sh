#!/usr/bin/env bash
set -euo pipefail

# Lightweight smoke checks for deployed AWS dev stacks.
#
# Scope:
# - Validates selected stack outputs exist and key resources are reachable.
# - Runs only shallow checks (no heavy end-to-end business flow validation).

APP_NAME="${APP_NAME:-cv-match}"
STAGE="${STAGE:-dev}"
REGION="${AWS_REGION:-us-east-1}"
STACK_SELECTOR="${STACK:-full}"

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" >&2
  exit 1
fi

log() {
  echo "[smoke] $1"
}

resolve_stack_name() {
  local selector="$1"
  case "${selector}" in
    network|security|compute|auth|data|profile|gateway)
      echo "${APP_NAME}-${STAGE}-${selector}"
      ;;
    *)
      echo "${selector}"
      ;;
  esac
}

stack_output() {
  local stack_name="$1"
  local output_key="$2"
  aws cloudformation describe-stacks \
    --stack-name "${stack_name}" \
    --region "${REGION}" \
    --query "Stacks[0].Outputs[?OutputKey=='${output_key}'].OutputValue | [0]" \
    --output text
}

assert_non_empty() {
  local value="$1"
  local message="$2"
  if [[ -z "${value}" || "${value}" == "None" ]]; then
    echo "[smoke] FAIL: ${message}" >&2
    exit 1
  fi
  log "PASS: ${message}"
}

assert_http_200() {
  local url="$1"
  local label="$2"
  local status
  status="$(curl -fsS -o /dev/null -w "%{http_code}" "${url}")"
  if [[ "${status}" != "200" ]]; then
    echo "[smoke] FAIL: ${label} expected 200, got ${status}" >&2
    exit 1
  fi
  log "PASS: ${label} returned 200"
}

assert_stack_exists() {
  local stack_name="$1"
  local status
  status="$(aws cloudformation describe-stacks \
    --stack-name "${stack_name}" \
    --region "${REGION}" \
    --query "Stacks[0].StackStatus" \
    --output text)"

  case "${status}" in
    CREATE_COMPLETE|UPDATE_COMPLETE|UPDATE_ROLLBACK_COMPLETE)
      log "PASS: ${stack_name} status ${status}"
      ;;
    *)
      echo "[smoke] FAIL: ${stack_name} not in a healthy deployed state (${status})" >&2
      exit 1
      ;;
  esac
}

assert_ecs_service_healthy() {
  local stack_name="$1"
  local label="$2"
  local service_arn
  local cluster_name
  local service_name
  local service_status
  local desired_count
  local running_count

  service_arn="$(aws cloudformation describe-stack-resources \
    --stack-name "${stack_name}" \
    --region "${REGION}" \
    --query "StackResources[?ResourceType=='AWS::ECS::Service'].PhysicalResourceId | [0]" \
    --output text)"

  assert_non_empty "${service_arn}" "${stack_name} exports ECS service resource"

  cluster_name="$(echo "${service_arn}" | awk -F'/' '{print $(NF-1)}')"
  service_name="$(echo "${service_arn}" | awk -F'/' '{print $NF}')"

  service_status="$(aws ecs describe-services \
    --cluster "${cluster_name}" \
    --services "${service_name}" \
    --region "${REGION}" \
    --query "services[0].status" \
    --output text)"

  desired_count="$(aws ecs describe-services \
    --cluster "${cluster_name}" \
    --services "${service_name}" \
    --region "${REGION}" \
    --query "services[0].desiredCount" \
    --output text)"

  running_count="$(aws ecs describe-services \
    --cluster "${cluster_name}" \
    --services "${service_name}" \
    --region "${REGION}" \
    --query "services[0].runningCount" \
    --output text)"

  if [[ "${service_status}" != "ACTIVE" ]]; then
    echo "[smoke] FAIL: ${label} ECS service is not ACTIVE (status=${service_status})" >&2
    exit 1
  fi

  if [[ "${desired_count}" == "None" || -z "${desired_count}" || "${desired_count}" -lt 1 ]]; then
    echo "[smoke] FAIL: ${label} ECS desired task count must be >= 1 (desired=${desired_count})" >&2
    exit 1
  fi

  if [[ "${running_count}" == "None" || -z "${running_count}" || "${running_count}" -lt 1 ]]; then
    echo "[smoke] FAIL: ${label} ECS running task count must be >= 1 (running=${running_count})" >&2
    exit 1
  fi

  log "PASS: ${label} ECS service is ACTIVE with desired=${desired_count}, running=${running_count}"
}

check_network() {
  local stack_name="$1"
  local vpc_id
  vpc_id="$(stack_output "${stack_name}" "VpcId")"
  assert_non_empty "${vpc_id}" "${stack_name} exports VpcId"
  aws ec2 describe-vpcs --vpc-ids "${vpc_id}" --region "${REGION}" >/dev/null
  log "PASS: ${stack_name} VPC exists (${vpc_id})"
}

check_security() {
  local stack_name="$1"
  local service_sg
  local db_sg
  service_sg="$(stack_output "${stack_name}" "ServiceSecurityGroupId")"
  db_sg="$(stack_output "${stack_name}" "DatabaseSecurityGroupId")"
  assert_non_empty "${service_sg}" "${stack_name} exports ServiceSecurityGroupId"
  assert_non_empty "${db_sg}" "${stack_name} exports DatabaseSecurityGroupId"
  aws ec2 describe-security-groups --group-ids "${service_sg}" "${db_sg}" --region "${REGION}" >/dev/null
  log "PASS: ${stack_name} security groups exist"
}

check_compute() {
  local stack_name="$1"
  local cluster_name
  cluster_name="$(stack_output "${stack_name}" "SharedEcsClusterName")"
  assert_non_empty "${cluster_name}" "${stack_name} exports SharedEcsClusterName"
  aws ecs describe-clusters --clusters "${cluster_name}" --region "${REGION}" >/dev/null
  log "PASS: ${stack_name} shared ECS cluster exists (${cluster_name})"
}

check_auth() {
  local stack_name="$1"
  local jwks_url
  jwks_url="$(stack_output "${stack_name}" "CognitoJwksUrl")"
  assert_non_empty "${jwks_url}" "${stack_name} exports CognitoJwksUrl"
  assert_http_200 "${jwks_url}" "${stack_name} JWKS endpoint"
}

check_data() {
  local stack_name="$1"
  local db_endpoint
  local secret_arn
  local bucket_name
  db_endpoint="$(stack_output "${stack_name}" "DatabaseEndpointAddress")"
  secret_arn="$(stack_output "${stack_name}" "DatabaseSecretArn")"
  bucket_name="$(stack_output "${stack_name}" "CvBucketName")"

  assert_non_empty "${db_endpoint}" "${stack_name} exports DatabaseEndpointAddress"
  assert_non_empty "${secret_arn}" "${stack_name} exports DatabaseSecretArn"
  assert_non_empty "${bucket_name}" "${stack_name} exports CvBucketName"

  aws secretsmanager describe-secret --secret-id "${secret_arn}" --region "${REGION}" >/dev/null
  aws s3api head-bucket --bucket "${bucket_name}" >/dev/null
  log "PASS: ${stack_name} secret and bucket exist"
}

check_profile() {
  local stack_name="$1"
  local profile_url
  local log_group
  profile_url="$(stack_output "${stack_name}" "ProfileServiceUrl")"
  log_group="$(stack_output "${stack_name}" "ProfileServiceLogGroupName")"
  assert_non_empty "${profile_url}" "${stack_name} exports ProfileServiceUrl"
  assert_non_empty "${log_group}" "${stack_name} exports ProfileServiceLogGroupName"
  assert_ecs_service_healthy "${stack_name}" "${stack_name}"
  aws logs describe-log-groups --log-group-name-prefix "${log_group}" --region "${REGION}" >/dev/null
  log "PASS: ${stack_name} log group visible"
}

check_gateway() {
  local stack_name="$1"
  local gateway_url
  local log_group
  gateway_url="$(stack_output "${stack_name}" "GatewayServiceUrl")"
  log_group="$(stack_output "${stack_name}" "GatewayServiceLogGroupName")"

  assert_non_empty "${gateway_url}" "${stack_name} exports GatewayServiceUrl"
  assert_non_empty "${log_group}" "${stack_name} exports GatewayServiceLogGroupName"
  assert_ecs_service_healthy "${stack_name}" "${stack_name}"

  assert_http_200 "${gateway_url}/health" "${stack_name} health endpoint"
  assert_http_200 "${gateway_url}/api/v1/locations/countries?limit=5" "${stack_name} public catalog endpoint"
  aws logs describe-log-groups --log-group-name-prefix "${log_group}" --region "${REGION}" >/dev/null
  log "PASS: ${stack_name} log group visible"
}

selected=("network" "security" "compute" "auth" "data" "profile" "gateway")
if [[ "${STACK_SELECTOR}" != "full" ]]; then
  IFS=',' read -r -a selected <<< "${STACK_SELECTOR}"
fi

for selector in "${selected[@]}"; do
  trimmed="$(echo "${selector}" | xargs)"
  [[ -z "${trimmed}" ]] && continue
  stack_name="$(resolve_stack_name "${trimmed}")"

  assert_stack_exists "${stack_name}"

  case "${trimmed}" in
    network)
      check_network "${stack_name}"
      ;;
    security)
      check_security "${stack_name}"
      ;;
    compute)
      check_compute "${stack_name}"
      ;;
    auth)
      check_auth "${stack_name}"
      ;;
    data)
      check_data "${stack_name}"
      ;;
    profile)
      check_profile "${stack_name}"
      ;;
    gateway)
      check_gateway "${stack_name}"
      ;;
    *)
      log "skip: unsupported selector '${trimmed}'"
      ;;
  esac
done

log "all lightweight smoke checks passed"