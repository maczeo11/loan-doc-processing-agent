#!/usr/bin/env bash
# ==============================================================================
# FinScan AI: Safe Deployment Automation Script (Phase 7)
# Deploys explicit release tag or Git SHA safely.
# Preserves previous release reference and enforces migration & health checks.
#
# Systemd-native deploy model: only Postgres/Redis/Caddy run in Docker (stock
# images, never rebuilt); api/worker/outbox-dispatcher run natively via
# systemd. See docs/deployment_guide.md for the full architecture and the
# one-time bootstrap this replaces.
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
echo "[1/6] Preserving active release reference..."
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
echo "[2/6] Fetching and checking out target release: ${TARGET_REF}..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    git fetch --tags origin || true
    # Checkout target ref non-destructively
    git checkout "${TARGET_REF}"
fi

# 4. Apply Release Version Stamp
echo "[3/6] Applying version metadata stamp to .env..."
if [ -f "${SCRIPT_DIR}/version.sh" ]; then
    chmod +x "${SCRIPT_DIR}/version.sh"
    "${SCRIPT_DIR}/version.sh" --env "${ROOT_DIR}/.env"
fi

# 5. Ensure db/redis are up, install/refresh deps + build UI, migrate, restart
# the native systemd services. No image build happens anymore - api/worker/
# outbox-dispatcher run directly on the host.
echo "[4/6] Ensuring db/pgbouncer/redis containers are up..."
docker compose -f "${COMPOSE_FILE}" up -d db pgbouncer redis

echo "[5/6] Installing Python deps, building UI, running migrations..."
chmod +x "${SCRIPT_DIR}/setup_venv.sh"
"${SCRIPT_DIR}/setup_venv.sh"
"${ROOT_DIR}/.venv/bin/alembic" upgrade head

echo "[6/6] Syncing systemd unit files and restarting native services..."
# Unit files under infra/systemd/ are NOT symlinked into /etc/systemd/system -
# without this, a change to a .service file (e.g. the gunicorn ExecStart
# below) would sit unused in the repo forever after `git checkout` while the
# box kept running whatever was installed at first bootstrap.
sudo cp "${SCRIPT_DIR}/systemd/"*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart finscan-api finscan-worker finscan-outbox-dispatcher
# Re-create Caddy too in case Caddyfile.production or docker-compose.yml
# changed (e.g. DOMAIN_NAME) - cheap since it's a stock image, no build.
docker compose -f "${COMPOSE_FILE}" up -d --force-recreate caddy

# 6. Verify Health Check
echo "Performing runtime health verification..."
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

    # Warm up every gunicorn worker before calling this deploy "done": the
    # single curl above only ever reached ONE of the N worker processes
    # (apps/api/main.py's own startup hook already eagerly loads the RAG
    # policy index per-worker, but each worker's DB connection pool and OS
    # page cache are still cold until it serves at least one real request).
    # Without this, the first judge/underwriter request to land on whichever
    # worker DIDN'T get the curl above pays that cold-start cost live during
    # the demo instead of here, right after deploy, where nobody's watching.
    READY_URL="http://localhost/health/ready"
    WARMUP_REQUESTS=$(( ${API_WORKERS:-4} * 2 ))
    echo "Warming ${WARMUP_REQUESTS} requests across API workers..."
    for i in $(seq 1 "${WARMUP_REQUESTS}"); do
        curl -sf "${READY_URL}" > /dev/null 2>&1 || true
    done

    # Reclaim disk: with only stock images (postgres/pgbouncer/redis/caddy) left in
    # Docker, this is now mostly routine hygiene rather than the load-bearing
    # fix it was under the old all-Docker model - but still safe/cheap to run.
    echo "Pruning dangling images and capping build cache..."
    docker image prune -f || true
    docker builder prune -f --keep-storage 5GB || true

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
    journalctl -u finscan-api -n 50 --no-pager || true
    echo ""
    echo "Deployment FAILED. To restore the previous release, run:"
    echo "  ${SCRIPT_DIR}/rollback.sh"
    echo "=================================================================="
    exit 1
fi
