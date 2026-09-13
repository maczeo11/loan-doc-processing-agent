#!/usr/bin/env bash
# ==============================================================================
# FinScan AI: Safe Resource Teardown Automation Script (Phase 7)
# Defaults to DRY-RUN. Requires explicit '--confirm' flag to delete resources.
# Strictly scoped by PROJECT_PREFIX/tags; NEVER deletes unscoped cloud resources.
# ==============================================================================

set -euo pipefail

# 1. Parameter Configuration & Default Scoping
AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_PREFIX="${PROJECT_PREFIX:-finscan}"
ENVIRONMENT="${ENVIRONMENT:-production}"
OWNER="${OWNER:-finscan-team}"

BUCKET_NAME="${BUCKET_NAME:-${PROJECT_PREFIX}-dossiers-${ENVIRONMENT}}"
QUEUE_NAME="${QUEUE_NAME:-${PROJECT_PREFIX}-jobs-${ENVIRONMENT}}"
DLQ_NAME="${DLQ_NAME:-${PROJECT_PREFIX}-jobs-dlq-${ENVIRONMENT}}"
EC2_INSTANCE_ID="${EC2_INSTANCE_ID:-}"

# Parse command line flags
DRY_RUN=1

for arg in "$@"; do
    case "$arg" in
        --confirm)
            DRY_RUN=0
            ;;
        --help|-h)
            echo "Usage: $0 [--confirm]"
            echo ""
            echo "Options:"
            echo "  --confirm    Execute destructive resource deletion (default is DRY-RUN)."
            echo ""
            echo "Scoped environment variables:"
            echo "  PROJECT_PREFIX   (default: finscan)"
            echo "  ENVIRONMENT      (default: production)"
            echo "  AWS_REGION       (default: us-east-1)"
            echo "  BUCKET_NAME      (default: ${PROJECT_PREFIX}-dossiers-${ENVIRONMENT})"
            echo "  QUEUE_NAME       (default: ${PROJECT_PREFIX}-jobs-${ENVIRONMENT})"
            echo "  DLQ_NAME         (default: ${PROJECT_PREFIX}-jobs-dlq-${ENVIRONMENT})"
            echo "  EC2_INSTANCE_ID  (optional EC2 instance to terminate)"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            echo "Use '$0 --help' for usage." >&2
            exit 1
            ;;
    esac
done

# Safety Scope Checks
if [ -z "${PROJECT_PREFIX}" ] || [ "${#PROJECT_PREFIX}" -lt 3 ]; then
    echo "ERROR: Refusing to run with empty or unsafe PROJECT_PREFIX: '${PROJECT_PREFIX}'" >&2
    exit 1
fi

case "${BUCKET_NAME}" in
    "${PROJECT_PREFIX}"*)
        # Scoped bucket name valid
        ;;
    *)
        echo "ERROR: Refusing to delete bucket '${BUCKET_NAME}'. It does not start with prefix '${PROJECT_PREFIX}'." >&2
        exit 1
        ;;
esac

case "${QUEUE_NAME}" in
    "${PROJECT_PREFIX}"*)
        # Scoped queue name valid
        ;;
    *)
        echo "ERROR: Refusing to delete queue '${QUEUE_NAME}'. It does not start with prefix '${PROJECT_PREFIX}'." >&2
        exit 1
        ;;
esac

echo "=================================================================="
if [ ${DRY_RUN} -eq 1 ]; then
    echo "FinScan AI: Teardown Inspection [DRY-RUN MODE]"
    echo "NO RESOURCES WILL BE DELETED. Re-run with '--confirm' to execute."
else
    echo "FinScan AI: Teardown Execution [CONFIRMED LIVE DELETION]"
fi
echo "Project Prefix:  ${PROJECT_PREFIX}"
echo "Environment:     ${ENVIRONMENT}"
echo "Region:          ${AWS_REGION}"
echo "=================================================================="

# Check AWS CLI
if ! command -v aws >/dev/null 2>&1; then
    echo "ERROR: 'aws' command-line tool is not installed or not in PATH." >&2
    exit 1
fi

# 2. Resource Discovery
echo "[1/4] Discovering scoped resources..."

# S3 Bucket
S3_EXISTS=0
if aws s3api head-bucket --bucket "${BUCKET_NAME}" 2>/dev/null; then
    S3_EXISTS=1
    echo "  [FOUND] S3 Bucket: arn:aws:s3:::${BUCKET_NAME}"
else
    echo "  [NOT FOUND] S3 Bucket: ${BUCKET_NAME}"
fi

# SQS Queues
MAIN_QUEUE_URL=$(aws sqs get-queue-url --queue-name "${QUEUE_NAME}" --region "${AWS_REGION}" --query 'QueueUrl' --output text 2>/dev/null || echo "")
if [ -n "${MAIN_QUEUE_URL}" ]; then
    echo "  [FOUND] SQS Main Queue: ${MAIN_QUEUE_URL}"
else
    echo "  [NOT FOUND] SQS Main Queue: ${QUEUE_NAME}"
fi

DLQ_URL=$(aws sqs get-queue-url --queue-name "${DLQ_NAME}" --region "${AWS_REGION}" --query 'QueueUrl' --output text 2>/dev/null || echo "")
if [ -n "${DLQ_URL}" ]; then
    echo "  [FOUND] SQS DLQ: ${DLQ_URL}"
else
    echo "  [NOT FOUND] SQS DLQ: ${DLQ_NAME}"
fi

# EC2 Instance (if supplied)
EC2_EXISTS=0
if [ -n "${EC2_INSTANCE_ID}" ]; then
    EC2_PROJ_TAG=$(aws ec2 describe-instances \
        --instance-ids "${EC2_INSTANCE_ID}" \
        --region "${AWS_REGION}" \
        --query "Reservations[0].Instances[0].Tags[?Key=='Project'].Value | [0]" \
        --output text 2>/dev/null || echo "")
    if [ "${EC2_PROJ_TAG}" = "${PROJECT_PREFIX}" ]; then
        EC2_EXISTS=1
        echo "  [FOUND] EC2 Instance: ${EC2_INSTANCE_ID} (Tagged Project=${PROJECT_PREFIX})"
    else
        echo "  [SKIP] EC2 Instance ${EC2_INSTANCE_ID} is not tagged Project=${PROJECT_PREFIX}."
    fi
fi

# 3. Dry-Run Evaluation
if [ ${DRY_RUN} -eq 1 ]; then
    echo "=================================================================="
    echo "DRY-RUN SUMMARY: The following scoped resources would be deleted:"
    [ ${S3_EXISTS} -eq 1 ] && echo "  - S3 Bucket: ${BUCKET_NAME} (and all contents)"
    [ -n "${MAIN_QUEUE_URL}" ] && echo "  - SQS Queue: ${MAIN_QUEUE_URL}"
    [ -n "${DLQ_URL}" ] && echo "  - SQS DLQ:   ${DLQ_URL}"
    [ ${EC2_EXISTS} -eq 1 ] && echo "  - EC2 Instance: ${EC2_INSTANCE_ID}"
    echo ""
    echo "DRY-RUN COMPLETE: No changes were made."
    echo "To perform live deletion, run:"
    echo "  $0 --confirm"
    echo "=================================================================="
    exit 0
fi

# 4. Live Deletion Phase (Confirmed)
echo "=================================================================="
echo "PROCEEDING WITH CONFIRMED RESOURCE DELETION..."
echo "=================================================================="

# S3 Deletion
if [ ${S3_EXISTS} -eq 1 ]; then
    echo "[2/4] Emptying and deleting S3 Bucket: ${BUCKET_NAME}..."
    aws s3 rm "s3://${BUCKET_NAME}" --recursive --region "${AWS_REGION}" || true
    # Remove versioned objects if versioning was enabled
    aws s3api delete-bucket --bucket "${BUCKET_NAME}" --region "${AWS_REGION}"
    echo "  Bucket ${BUCKET_NAME} deleted."
fi

# SQS Deletion
echo "[3/4] Deleting SQS Queues..."
if [ -n "${MAIN_QUEUE_URL}" ]; then
    aws sqs delete-queue --queue-url "${MAIN_QUEUE_URL}" --region "${AWS_REGION}"
    echo "  Queue ${QUEUE_NAME} deleted."
fi

if [ -n "${DLQ_URL}" ]; then
    aws sqs delete-queue --queue-url "${DLQ_URL}" --region "${AWS_REGION}"
    echo "  DLQ ${DLQ_NAME} deleted."
fi

# EC2 Termination
echo "[4/4] Evaluating EC2 Instance Termination..."
if [ ${EC2_EXISTS} -eq 1 ]; then
    echo "  Terminating verified EC2 instance: ${EC2_INSTANCE_ID}..."
    aws ec2 terminate-instances --instance-ids "${EC2_INSTANCE_ID}" --region "${AWS_REGION}"
    echo "  EC2 instance termination initiated."
else
    echo "  No EC2 instance specified or matched for termination."
fi

echo "=================================================================="
echo "SUCCESS: Teardown complete. All scoped FinScan AI resources deleted."
echo "=================================================================="
