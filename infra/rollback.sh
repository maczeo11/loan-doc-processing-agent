#!/usr/bin/env bash
# ==============================================================================
# FinScan AI: Safe Rollback Automation Script (Phase 7)
# Restores previous release reference or explicit target tag/SHA.
# Performs non-destructive checkout, restarts services, and verifies health check.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

CURRENT_RELEASE_FILE="${ROOT_DIR}/.current_release"
PREVIOUS_RELEASE_FILE="${ROOT_DIR}/.previous_release"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"

# 1. Determine Target Rollback Release
EXPLICIT_TARGET="${1:-}"

if [ -n "${EXPLICIT_TARGET}" ]; then
    ROLLBACK_REF="${EXPLICIT_TARGET}"
    echo "Using explicit target rollback ref: ${ROLLBACK_REF}"
elif [ -f "${PREVIOUS_RELEASE_FILE}" ]; then
    ROLLBACK_REF=$(cat "${PREVIOUS_RELEASE_FILE}")
    echo "Using recorded previous release ref: ${ROLLBACK_REF}"
else
    echo "ERROR: No target specified and no previous release found in ${PREVIOUS_RELEASE_FILE}." >&2
    echo "Usage: $0 [RELEASE_TAG_OR_SHA]" >&2
    exit 1
fi

if [ -z "${ROLLBACK_REF}" ] || [ "${ROLLBACK_REF}" = "unknown" ]; then
    echo "ERROR: Invalid rollback reference: '${ROLLBACK_REF}'." >&2
    exit 1
fi

echo "=================================================================="
echo "FinScan AI: Initiating Rollback"
echo "Rollback Target Ref: ${ROLLBACK_REF}"
echo "Deploy Directory:    ${ROOT_DIR}"
echo "=================================================================="

# 2. Checkout Target Rollback Release Non-Destructively
echo "[1/4] Checking out rollback target ref: ${ROLLBACK_REF}..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    git fetch --tags origin || true
    # Checkout non-destructively
    git checkout "${ROLLBACK_REF}"
fi

# 3. Apply Version Metadata
echo "[2/4] Updating release version stamp in .env..."
if [ -f "${SCRIPT_DIR}/version.sh" ]; then
    chmod +x "${SCRIPT_DIR}/version.sh"
    "${SCRIPT_DIR}/version.sh" --env "${ROOT_DIR}/.env"
fi

# 4. Restart Services
echo "[3/4] Restarting containers with rollback image..."
docker compose -f "${COMPOSE_FILE}" up -d db redis
docker compose -f "${COMPOSE_FILE}" up --build -d migrate api outbox-dispatcher worker caddy

# 5. Health Check Verification
echo "[4/4] Verifying health check on rollback deployment..."
HEALTH_URL="http://localhost/health"
MAX_RETRIES=30
RETRY_COUNT=0
HEALTHY=0

while [ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]; do
    if curl -sf "${HEALTH_URL}" > /dev/null 2>&1; then
        HEALTHY=1
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "  Waiting for healthy response from ${HEALTH_URL}... (${RETRY_COUNT}/${MAX_RETRIES})"
    sleep 2
done

if [ ${HEALTHY} -eq 1 ]; then
    echo "${ROLLBACK_REF}" > "${CURRENT_RELEASE_FILE}"
    HEALTH_OUTPUT=$(curl -s "${HEALTH_URL}")
    echo "=================================================================="
    echo "SUCCESS: Rollback completed and verified healthy!"
    echo "Active Release: ${ROLLBACK_REF}"
    echo "Health Status:  ${HEALTH_OUTPUT}"
    echo "=================================================================="
    exit 0
else
    echo "=================================================================="
    echo "ERROR: Health check failed during rollback after ${MAX_RETRIES} attempts!"
    docker compose -f "${COMPOSE_FILE}" logs --tail=50 api || true
    echo "=================================================================="
    exit 1
fi
