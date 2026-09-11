#!/usr/bin/env bash
# ==============================================================================
# FinScan AI: CloudFront CDN Setup for React SPA (Phase 7)
# Creates a private S3 bucket for UI static assets, uploads the built SPA,
# and provisions a CloudFront distribution with Origin Access Control (OAC).
#
# Budget impact: $0.00 (AWS Free Tier: 1 TB/mo transfer, 10M requests/mo)
#
# Prerequisites:
#   - AWS CLI v2 configured with valid credentials
#   - React SPA already built: apps/ui/dist/ exists
#   - aws_setup.sh already run (S3 dossiers bucket + SQS provisioned)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_PREFIX="${PROJECT_PREFIX:-finscan}"
ENVIRONMENT="${ENVIRONMENT:-production}"
UI_BUCKET_NAME="${UI_BUCKET_NAME:-${PROJECT_PREFIX}-ui-assets-${ENVIRONMENT}}"
DOMAIN_NAME="${DOMAIN_NAME:-}"
UI_DIST_DIR="${ROOT_DIR}/apps/ui/dist"

echo "=================================================================="
echo "FinScan AI: CloudFront CDN Provisioning"
echo "Region:          ${AWS_REGION}"
echo "UI Bucket:       ${UI_BUCKET_NAME}"
echo "UI Dist Dir:     ${UI_DIST_DIR}"
echo "=================================================================="

# Verify dist exists
if [ ! -d "${UI_DIST_DIR}" ]; then
    echo "ERROR: React SPA build not found at ${UI_DIST_DIR}"
    echo "Run 'cd apps/ui && npm run build' first."
    exit 1
fi

# Check AWS CLI
if ! command -v aws >/dev/null 2>&1; then
    echo "ERROR: 'aws' CLI not found." >&2
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Connected as Account ID: ${AWS_ACCOUNT_ID}"

# ------------------------------------------------------------------------------
# 1. Create Private S3 Bucket for UI Assets
# ------------------------------------------------------------------------------
echo "[1/5] Creating S3 bucket for UI assets: ${UI_BUCKET_NAME}..."

if aws s3api head-bucket --bucket "${UI_BUCKET_NAME}" 2>/dev/null; then
    echo "  Bucket already exists."
else
    if [ "${AWS_REGION}" = "us-east-1" ]; then
        aws s3api create-bucket --bucket "${UI_BUCKET_NAME}" --region "${AWS_REGION}"
    else
        aws s3api create-bucket --bucket "${UI_BUCKET_NAME}" --region "${AWS_REGION}" \
            --create-bucket-configuration LocationConstraint="${AWS_REGION}"
    fi
fi

# Block ALL public access (CloudFront uses OAC, not public S3)
aws s3api put-public-access-block \
    --bucket "${UI_BUCKET_NAME}" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "  Public access blocked."

# ------------------------------------------------------------------------------
# 2. Upload React SPA Build
# ------------------------------------------------------------------------------
echo "[2/5] Uploading React SPA to s3://${UI_BUCKET_NAME}/..."

# index.html: no-cache (CloudFront always fetches latest)
aws s3 cp "${UI_DIST_DIR}/index.html" "s3://${UI_BUCKET_NAME}/index.html" \
    --cache-control "no-cache, no-store, must-revalidate" \
    --content-type "text/html"

# Hashed assets (JS, CSS): long-lived cache (Vite adds content hashes)
aws s3 sync "${UI_DIST_DIR}/assets/" "s3://${UI_BUCKET_NAME}/assets/" \
    --cache-control "public, max-age=31536000, immutable" \
    --delete

# Everything else (favicon, manifest, etc.)
aws s3 sync "${UI_DIST_DIR}/" "s3://${UI_BUCKET_NAME}/" \
    --exclude "index.html" \
    --exclude "assets/*" \
    --cache-control "public, max-age=86400" \
    --delete

echo "  Upload complete."

# ------------------------------------------------------------------------------
# 3. Create CloudFront Origin Access Control (OAC)
# ------------------------------------------------------------------------------
echo "[3/5] Creating CloudFront Origin Access Control..."

OAC_NAME="${PROJECT_PREFIX}-ui-oac-${ENVIRONMENT}"

# Check if OAC already exists
EXISTING_OAC_ID=$(aws cloudfront list-origin-access-controls \
    --query "OriginAccessControlList.Items[?Name=='${OAC_NAME}'].Id" \
    --output text 2>/dev/null || echo "")

if [ -n "${EXISTING_OAC_ID}" ] && [ "${EXISTING_OAC_ID}" != "None" ]; then
    echo "  OAC already exists: ${EXISTING_OAC_ID}"
else
    OAC_RESULT=$(aws cloudfront create-origin-access-control \
        --origin-access-control-config "{
            \"Name\": \"${OAC_NAME}\",
            \"Description\": \"OAC for FinScan UI S3 bucket\",
            \"SigningProtocol\": \"sigv4\",
            \"SigningBehavior\": \"always\",
            \"OriginAccessControlOriginType\": \"s3\"
        }" \
        --query 'OriginAccessControl.Id' \
        --output text)
    EXISTING_OAC_ID="${OAC_RESULT}"
    echo "  Created OAC: ${EXISTING_OAC_ID}"
fi

# ------------------------------------------------------------------------------
# 4. Create CloudFront Distribution
# ------------------------------------------------------------------------------
echo "[4/5] Creating CloudFront distribution..."

S3_ORIGIN_DOMAIN="${UI_BUCKET_NAME}.s3.${AWS_REGION}.amazonaws.com"
CALLER_REF="finscan-ui-$(date +%s)"

DIST_CONFIG="{
    \"CallerReference\": \"${CALLER_REF}\",
    \"Comment\": \"FinScan AI React SPA (${ENVIRONMENT})\",
    \"Enabled\": true,
    \"DefaultRootObject\": \"index.html\",
    \"Origins\": {
        \"Quantity\": 1,
        \"Items\": [{
            \"Id\": \"S3-${UI_BUCKET_NAME}\",
            \"DomainName\": \"${S3_ORIGIN_DOMAIN}\",
            \"OriginAccessControlId\": \"${EXISTING_OAC_ID}\",
            \"S3OriginConfig\": {
                \"OriginAccessIdentity\": \"\"
            }
        }]
    },
    \"DefaultCacheBehavior\": {
        \"TargetOriginId\": \"S3-${UI_BUCKET_NAME}\",
        \"ViewerProtocolPolicy\": \"redirect-to-https\",
        \"AllowedMethods\": {
            \"Quantity\": 2,
            \"Items\": [\"GET\", \"HEAD\"]
        },
        \"CachePolicyId\": \"658327ea-f89d-4fab-a63d-7e88639e58f6\",
        \"Compress\": true
    },
    \"CustomErrorResponses\": {
        \"Quantity\": 2,
        \"Items\": [
            {
                \"ErrorCode\": 403,
                \"ResponsePagePath\": \"/index.html\",
                \"ResponseCode\": \"200\",
                \"ErrorCachingMinTTL\": 10
            },
            {
                \"ErrorCode\": 404,
                \"ResponsePagePath\": \"/index.html\",
                \"ResponseCode\": \"200\",
                \"ErrorCachingMinTTL\": 10
            }
        ]
    },
    \"ViewerCertificate\": {
        \"CloudFrontDefaultCertificate\": true
    }
}"

DISTRIBUTION_ID=$(aws cloudfront create-distribution \
    --distribution-config "${DIST_CONFIG}" \
    --query 'Distribution.Id' \
    --output text 2>/dev/null || echo "")

if [ -z "${DISTRIBUTION_ID}" ]; then
    echo "  WARNING: CloudFront distribution creation failed or already exists."
    echo "  Check the AWS console for existing distributions."
else
    CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution \
        --id "${DISTRIBUTION_ID}" \
        --query 'Distribution.DomainName' \
        --output text)
    echo "  Distribution ID: ${DISTRIBUTION_ID}"
    echo "  CloudFront Domain: ${CLOUDFRONT_DOMAIN}"
fi

# ------------------------------------------------------------------------------
# 5. Set S3 Bucket Policy to Allow CloudFront OAC
# ------------------------------------------------------------------------------
echo "[5/5] Applying S3 bucket policy for CloudFront OAC..."

if [ -n "${DISTRIBUTION_ID}" ]; then
    BUCKET_POLICY="{
        \"Version\": \"2012-10-17\",
        \"Statement\": [{
            \"Sid\": \"AllowCloudFrontServicePrincipalReadOnly\",
            \"Effect\": \"Allow\",
            \"Principal\": {
                \"Service\": \"cloudfront.amazonaws.com\"
            },
            \"Action\": \"s3:GetObject\",
            \"Resource\": \"arn:aws:s3:::${UI_BUCKET_NAME}/*\",
            \"Condition\": {
                \"StringEquals\": {
                    \"AWS:SourceArn\": \"arn:aws:cloudfront::${AWS_ACCOUNT_ID}:distribution/${DISTRIBUTION_ID}\"
                }
            }
        }]
    }"

    aws s3api put-bucket-policy \
        --bucket "${UI_BUCKET_NAME}" \
        --policy "${BUCKET_POLICY}"

    echo "  Bucket policy applied."
fi

echo "=================================================================="
echo "FinScan AI: CloudFront CDN Provisioning Complete"
echo "=================================================================="
if [ -n "${CLOUDFRONT_DOMAIN:-}" ]; then
    echo ""
    echo "React SPA URL:  https://${CLOUDFRONT_DOMAIN}"
    echo ""
    echo "IMPORTANT: Set this in your React build environment:"
    echo "  VITE_API_BASE_URL=https://${DOMAIN_NAME:-your-ec2-domain.com}"
    echo ""
    echo "To update the SPA after code changes:"
    echo "  cd apps/ui && npm run build"
    echo "  aws s3 sync dist/ s3://${UI_BUCKET_NAME}/ --delete"
    echo "  aws cloudfront create-invalidation --distribution-id ${DISTRIBUTION_ID} --paths '/*'"
fi
echo "=================================================================="
