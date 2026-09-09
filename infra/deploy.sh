#!/usr/bin/env bash
# ==============================================================================
# FinScan AI: Safe Deployment Automation Script (Phase 7)
# Deploys explicit release tag or Git SHA safely.
# Preserves previous release reference and enforces migration & health checks.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

CURRENT_RELEASE_FILE="${ROOT_DIR}/.current_release"
PREVIOUS_RELEASE_FILE="${ROOT_DIR}/.previous_release"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"

# 1. Determine Target Release
TARGET_REF="${1:-}"
if [ -z "${TARGET_REF}" ]; then
    if git rev-parse --git-dir > /dev/null 2>&1; then
        TARGET_REF=$(git rev-parse HEAD)
    else
        echo "ERROR: Target release tag or commit SHA must be provided when not in a git repo." >&2
        echo "Usage: $0 <RELEASE_TAG_OR_SHA>" >&2
        exit 1
    fi
fi

echo "=================================================================="
echo "FinScan AI: Initiating Deployment"
echo "Target Release Ref: ${TARGET_REF}"
echo "Deploy Directory:   ${ROOT_DIR}"
echo "=================================================================="

# 2. Preserve Currently Running Release Reference
echo "[1/5] Preserving active release reference..."
if [ -f "${CURRENT_RELEASE_FILE}" ]; then
    cp "${CURRENT_RELEASE_FILE}" "${PREVIOUS_RELEASE_FILE}"
    PREV_REF=$(cat "${PREVIOUS_RELEASE_FILE}")
    echo "  Previous release recorded: ${PREV_REF}"
elif git rev-parse --git-dir > /dev/null 2>&1; then
    PREV_REF=$(git rev-parse HEAD)
    echo "${PREV_REF}" > "${PREVIOUS_RELEASE_FILE}"
    echo "  Initial release recorded: ${PREV_REF}"
else
    echo "unknown" > "${PREVIOUS_RELEASE_FILE}"
fi

# 3. Checkout Target Release Non-Destructively
echo "[2/5] Fetching and checking out target release: ${TARGET_REF}..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    git fetch --tags origin || true
    # Checkout target ref non-destructively
    git checkout "${TARGET_REF}"
fi

# 4. Apply Release Version Stamp
echo "[3/5] Applying version metadata stamp to .env..."
if [ -f "${SCRIPT_DIR}/version.sh" ]; then
    chmod +x "${SCRIPT_DIR}/version.sh"
    "${SCRIPT_DIR}/version.sh" --env "${ROOT_DIR}/.env"
fi

# 5. Execute Migrations & Start Services
echo "[4/5] Running migrations and launching container services..."
# Ensure database and redis dependencies are healthy first
docker compose -f "${COMPOSE_FILE}" up -d db redis

# Execute one-shot Alembic migration
docker compose -f "${COMPOSE_FILE}" up --build -d migrate api outbox-dispatcher worker caddy

# 6. Verify Health Check
echo "[5/5] Performing runtime health verification..."
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
    echo "${TARGET_REF}" > "${CURRENT_RELEASE_FILE}"
    HEALTH_OUTPUT=$(curl -s "${HEALTH_URL}")
    echo "=================================================================="
    echo "SUCCESS: Deployment completed and verified healthy!"
    echo "Active Release: ${TARGET_REF}"
    echo "Health Status:  ${HEALTH_OUTPUT}"
    echo "=================================================================="
    exit 0
else
    echo "=================================================================="
    echo "ERROR: Health check failed after ${MAX_RETRIES} attempts!"
    echo "Service logs:"
    docker compose -f "${COMPOSE_FILE}" logs --tail=50 api || true
    echo ""
    echo "Deployment FAILED. To restore the previous release, run:"
    echo "  ${SCRIPT_DIR}/rollback.sh"
    echo "=================================================================="
    exit 1
fi
