#!/usr/bin/env sh
set -eu

echo "[localstack-init] bootstrapping local resources"

# Profile-owned storage resource
awslocal s3api create-bucket --bucket profile-cv-bucket >/dev/null 2>&1 || true

# CV parser-owned queue resources
awslocal sqs create-queue --queue-name cv-parser-dlq >/dev/null
DLQ_ARN="$(awslocal sqs get-queue-attributes \
  --queue-url http://localhost:4566/000000000000/cv-parser-dlq \
  --attribute-names QueueArn \
  --query Attributes.QueueArn \
  --output text)"

awslocal sqs create-queue --queue-name cv-parser-queue >/dev/null
awslocal sqs set-queue-attributes \
  --queue-url http://localhost:4566/000000000000/cv-parser-queue \
  --attributes "{\"VisibilityTimeout\":\"300\",\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"${DLQ_ARN}\\\",\\\"maxReceiveCount\\\":\\\"5\\\"}\"}" >/dev/null

echo "[localstack-init] resources ready"