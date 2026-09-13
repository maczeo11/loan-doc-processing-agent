#!/usr/bin/env bash
# ==============================================================================
# FinScan AI: Cost Control Script - Start EC2 Instance (Phase 7)
# Starts the explicitly configured EC2 instance and outputs its public endpoints.
# ==============================================================================

set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
EC2_INSTANCE_ID="${EC2_INSTANCE_ID:-${1:-}}"

if [ -z "${EC2_INSTANCE_ID}" ]; then
    echo "ERROR: EC2_INSTANCE_ID is required to start the instance." >&2
    echo "Usage: $0 [INSTANCE_ID] or export EC2_INSTANCE_ID=i-xxxxxxxxx" >&2
    exit 1
fi

echo "=================================================================="
echo "FinScan AI: Starting EC2 Instance"
echo "Instance ID: ${EC2_INSTANCE_ID}"
echo "Region:      ${AWS_REGION}"
echo "=================================================================="

# Check AWS CLI
if ! command -v aws >/dev/null 2>&1; then
    echo "ERROR: 'aws' command-line tool is not installed or not in PATH." >&2
    exit 1
fi

echo "Verifying current instance state..."
CURRENT_STATE=$(aws ec2 describe-instances \
    --instance-ids "${EC2_INSTANCE_ID}" \
    --region "${AWS_REGION}" \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text 2>/dev/null || echo "not_found")

if [ "${CURRENT_STATE}" = "not_found" ]; then
    echo "ERROR: Instance '${EC2_INSTANCE_ID}' was not found in region '${AWS_REGION}'." >&2
    exit 1
fi

echo "Current instance state: ${CURRENT_STATE}"

if [ "${CURRENT_STATE}" != "running" ]; then
    echo "Sending start-instances command..."
    aws ec2 start-instances \
        --instance-ids "${EC2_INSTANCE_ID}" \
        --region "${AWS_REGION}" \
        --output table

    echo "Waiting for instance '${EC2_INSTANCE_ID}' to enter running state..."
    aws ec2 wait instance-running \
        --instance-ids "${EC2_INSTANCE_ID}" \
        --region "${AWS_REGION}"
fi

# Retrieve public network identifiers
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "${EC2_INSTANCE_ID}" \
    --region "${AWS_REGION}" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

PUBLIC_DNS=$(aws ec2 describe-instances \
    --instance-ids "${EC2_INSTANCE_ID}" \
    --region "${AWS_REGION}" \
    --query 'Reservations[0].Instances[0].PublicDnsName' \
    --output text)

echo "=================================================================="
echo "SUCCESS: Instance ${EC2_INSTANCE_ID} is now RUNNING."
echo "Public IP:  ${PUBLIC_IP}"
echo "Public DNS: ${PUBLIC_DNS}"
echo "HTTP URL:   http://${PUBLIC_IP}"
echo "=================================================================="
