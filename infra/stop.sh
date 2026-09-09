#!/usr/bin/env bash
# ==============================================================================
# FinScan AI: Cost Control Script - Stop EC2 Instance (Phase 7)
# Safely stops ONLY the explicitly configured EC2 instance to prevent idle cloud billing.
# ==============================================================================

set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
EC2_INSTANCE_ID="${EC2_INSTANCE_ID:-${1:-}}"

if [ -z "${EC2_INSTANCE_ID}" ]; then
    echo "ERROR: EC2_INSTANCE_ID is required to stop the instance." >&2
    echo "Usage: $0 [INSTANCE_ID] or export EC2_INSTANCE_ID=i-xxxxxxxxx" >&2
    exit 1
fi

echo "=================================================================="
echo "FinScan AI: Stopping EC2 Instance for Cost Control"
echo "Instance ID: ${EC2_INSTANCE_ID}"
echo "Region:      ${AWS_REGION}"
echo "=================================================================="

# Check AWS CLI
if ! command -v aws >/dev/null 2>&1; then
    echo "ERROR: 'aws' command-line tool is not installed or not in PATH." >&2
    exit 1
fi

echo "Verifying instance state..."
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

if [ "${CURRENT_STATE}" = "stopped" ]; then
    echo "Instance is already stopped. No action required."
    exit 0
fi

echo "Sending stop-instances command..."
aws ec2 stop-instances \
    --instance-ids "${EC2_INSTANCE_ID}" \
    --region "${AWS_REGION}" \
    --output table

echo "Waiting for instance '${EC2_INSTANCE_ID}' to enter stopped state..."
aws ec2 wait instance-stopped \
    --instance-ids "${EC2_INSTANCE_ID}" \
    --region "${AWS_REGION}"

echo "=================================================================="
echo "SUCCESS: Instance ${EC2_INSTANCE_ID} is now safely stopped."
echo "Hourly compute billing has ceased."
echo "=================================================================="
