#!/usr/bin/env bash
# ==============================================================================
# FinScan AI: AWS Infrastructure Provisioning Script (Phase 7)
# Creates private S3 bucket, SQS queue + DLQ, sets encryption, CORS, and lifecycle.
# Strictly parameterized and idempotent; never embeds hardcoded account IDs.
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# 1. Environment Configuration & Defaults
# ------------------------------------------------------------------------------
AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_PREFIX="${PROJECT_PREFIX:-finscan}"
ENVIRONMENT="${ENVIRONMENT:-production}"
OWNER="${OWNER:-finscan-team}"
RELEASE_VERSION="${RELEASE_VERSION:-1.0.0}"

# Resource names (parameterized with safe defaults)
BUCKET_NAME="${BUCKET_NAME:-${PROJECT_PREFIX}-dossiers-${ENVIRONMENT}}"
QUEUE_NAME="${QUEUE_NAME:-${PROJECT_PREFIX}-jobs-${ENVIRONMENT}}"
DLQ_NAME="${DLQ_NAME:-${PROJECT_PREFIX}-jobs-dlq-${ENVIRONMENT}}"
DOMAIN_NAME="${DOMAIN_NAME:-}"
EC2_INSTANCE_ID="${EC2_INSTANCE_ID:-}"

echo "=================================================================="
echo "FinScan AI: AWS Provisioning Setup"
echo "Region:          ${AWS_REGION}"
echo "Project Prefix:  ${PROJECT_PREFIX}"
echo "Environment:     ${ENVIRONMENT}"
echo "Owner:           ${OWNER}"
echo "Bucket Name:     ${BUCKET_NAME}"
echo "Queue Name:      ${QUEUE_NAME}"
echo "DLQ Name:        ${DLQ_NAME}"
echo "=================================================================="

# Check AWS CLI
if ! command -v aws >/dev/null 2>&1; then
    echo "ERROR: 'aws' command-line tool is not installed or not in PATH." >&2
    exit 1
fi

# Detect AWS Account ID dynamically
echo "[1/4] Detecting AWS Account Identity..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "  Connected as Account ID: ${AWS_ACCOUNT_ID}"

TAGS_KEY_VALUE="Project=${PROJECT_PREFIX},Environment=${ENVIRONMENT},Owner=${OWNER}"

# ------------------------------------------------------------------------------
# 2. S3 Bucket Provisioning (Private, Encrypted, Block Public, CORS, Lifecycle)
# ------------------------------------------------------------------------------
echo "[2/4] Provisioning S3 Dossiers Bucket: ${BUCKET_NAME}..."

if aws s3api head-bucket --bucket "${BUCKET_NAME}" 2>/dev/null; then
    echo "  Bucket '${BUCKET_NAME}' already exists. Reconciling policies..."
else
    echo "  Creating S3 bucket '${BUCKET_NAME}' in region '${AWS_REGION}'..."
    if [ "${AWS_REGION}" = "us-east-1" ]; then
        aws s3api create-bucket \
            --bucket "${BUCKET_NAME}" \
            --region "${AWS_REGION}"
    else
        aws s3api create-bucket \
            --bucket "${BUCKET_NAME}" \
            --region "${AWS_REGION}" \
            --create-bucket-configuration LocationConstraint="${AWS_REGION}"
    fi
fi

# A. Block Public Access (all 4 settings)
echo "  Enforcing S3 Block Public Access..."
aws s3api put-public-access-block \
    --bucket "${BUCKET_NAME}" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# B. Default Server-Side Encryption (AES256)
echo "  Enforcing Default SSE-S3 Encryption..."
aws s3api put-bucket-encryption \
    --bucket "${BUCKET_NAME}" \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }'

# C. Restrictive CORS (only for frontend domain or localhost)
echo "  Configuring Restrictive CORS policy..."
ALLOWED_ORIGIN="https://${DOMAIN_NAME:-localhost}"
aws s3api put-bucket-cors \
    --bucket "${BUCKET_NAME}" \
    --cors-configuration '{
        "CORSRules": [
            {
                "AllowedHeaders": ["*"],
                "AllowedMethods": ["GET", "PUT", "HEAD"],
                "AllowedOrigins": ["'"${ALLOWED_ORIGIN}"'"],
                "ExposeHeaders": ["ETag"],
                "MaxAgeSeconds": 3000
            }
        ]
    }'

# D. Lifecycle Policy (cleanup multipart uploads after 7 days, expire old tmp artifacts after 90 days)
echo "  Configuring S3 Lifecycle rules..."
aws s3api put-bucket-lifecycle-configuration \
    --bucket "${BUCKET_NAME}" \
    --lifecycle-configuration '{
        "Rules": [
            {
                "ID": "AbortIncompleteMultipartUploads",
                "Status": "Enabled",
                "Filter": {},
                "AbortIncompleteMultipartUpload": {
                    "DaysAfterInitiation": 7
                }
            },
            {
                "ID": "ExpireTemporaryArtifacts",
                "Status": "Enabled",
                "Filter": {
                    "Prefix": "tmp/"
                },
                "Expiration": {
                    "Days": 30
                }
            }
        ]
    }'

# E. Bucket Tagging
echo "  Tagging bucket..."
aws s3api put-bucket-tagging \
    --bucket "${BUCKET_NAME}" \
    --tagging "TagSet=[{Key=Project,Value=${PROJECT_PREFIX}},{Key=Environment,Value=${ENVIRONMENT}},{Key=Owner,Value=${OWNER}}]"

BUCKET_ARN="arn:aws:s3:::${BUCKET_NAME}"
echo "  Bucket ARN: ${BUCKET_ARN}"

# ------------------------------------------------------------------------------
# 3. SQS Queue & Dead-Letter Queue (DLQ) Provisioning
# ------------------------------------------------------------------------------
echo "[3/4] Provisioning SQS Queues..."

# A. Dead-Letter Queue (Retention: 14 days)
echo "  Creating Dead-Letter Queue: ${DLQ_NAME}..."
DLQ_URL=$(aws sqs create-queue \
    --queue-name "${DLQ_NAME}" \
    --region "${AWS_REGION}" \
    --attributes MessageRetentionPeriod=1209600 \
    --tags "Project=${PROJECT_PREFIX},Environment=${ENVIRONMENT},Owner=${OWNER}" \
    --query 'QueueUrl' \
    --output text)

DLQ_ARN=$(aws sqs get-queue-attributes \
    --queue-url "${DLQ_URL}" \
    --attribute-names QueueArn \
    --region "${AWS_REGION}" \
    --query 'Attributes.QueueArn' \
    --output text)

echo "  DLQ URL: ${DLQ_URL}"
echo "  DLQ ARN: ${DLQ_ARN}"

# B. Primary Job Queue with RedrivePolicy (maxReceiveCount=3)
echo "  Creating Primary Job Queue: ${QUEUE_NAME} with RedrivePolicy (maxReceiveCount=3)..."
REDRIVE_POLICY="{\"deadLetterTargetArn\":\"${DLQ_ARN}\",\"maxReceiveCount\":3}"

QUEUE_URL=$(aws sqs create-queue \
    --queue-name "${QUEUE_NAME}" \
    --region "${AWS_REGION}" \
    --attributes VisibilityTimeout=300,MessageRetentionPeriod=345600,RedrivePolicy="${REDRIVE_POLICY}" \
    --tags "Project=${PROJECT_PREFIX},Environment=${ENVIRONMENT},Owner=${OWNER}" \
    --query 'QueueUrl' \
    --output text)

QUEUE_ARN=$(aws sqs get-queue-attributes \
    --queue-url "${QUEUE_URL}" \
    --attribute-names QueueArn \
    --region "${AWS_REGION}" \
    --query 'Attributes.QueueArn' \
    --output text)

echo "  Primary Queue URL: ${QUEUE_URL}"
echo "  Primary Queue ARN: ${QUEUE_ARN}"

# ------------------------------------------------------------------------------
# 4. Generate Rendered IAM Policy Document
# ------------------------------------------------------------------------------
echo "[4/4] Generating rendered IAM Policy Document..."
POLICY_TEMPLATE="$(dirname "$0")/iam_policy.json"
POLICY_RENDERED="$(dirname "$0")/iam_policy.rendered.json"

if [ -f "${POLICY_TEMPLATE}" ]; then
    sed \
        -e "s|\\${BUCKET_NAME}|${BUCKET_NAME}|g" \
        -e "s|\\${AWS_REGION}|${AWS_REGION}|g" \
        -e "s|\\${AWS_ACCOUNT_ID}|${AWS_ACCOUNT_ID}|g" \
        -e "s|\\${QUEUE_NAME}|${QUEUE_NAME}|g" \
        -e "s|\\${DLQ_NAME}|${DLQ_NAME}|g" \
        "${POLICY_TEMPLATE}" > "${POLICY_RENDERED}"
    echo "  Rendered IAM policy saved to: ${POLICY_RENDERED}"
fi

echo "=================================================================="
echo "FinScan AI: AWS Provisioning Completed Successfully"
echo "=================================================================="
echo "S3_BUCKET:         ${BUCKET_NAME}"
echo "SQS_QUEUE_URL:     ${QUEUE_URL}"
echo "SQS_DLQ_URL:       ${DLQ_URL}"
echo ""
echo "Recommended .env configuration for EC2 production deployment:"
cat <<EOF
# --- FinScan AI Cloud Config ---
ENVIRONMENT=production
STORAGE_BACKEND=s3
S3_BUCKET=${BUCKET_NAME}
AWS_REGION=${AWS_REGION}
QUEUE_BACKEND=sqs
SQS_QUEUE_URL=${QUEUE_URL}
DOMAIN_NAME=${DOMAIN_NAME:-yourdomain.com}
RELEASE_VERSION=${RELEASE_VERSION}
EOF
echo "=================================================================="
