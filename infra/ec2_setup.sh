#!/usr/bin/env bash
# ==============================================================================
# FinScan AI: EC2 Host Bootstrap & Initialization Script (Phase 7)
#
# Systemd-native deploy model: installs Docker (for Postgres/Redis/Caddy
# only), Python 3.11 + Node 20 (for the native api/worker/outbox-dispatcher
# processes), builds the venv/UI, and installs (but does not yet start) the
# systemd units - the first real start happens via infra/deploy.sh. See
# docs/deployment_guide.md for the full architecture.
# ==============================================================================

set -euo pipefail

APP_DIR="/opt/finscan"
REPO_URL="${REPO_URL:-https://github.com/maczeo11/loan-doc-processing-agent.git}"
# NOTE: production actually uses an SSH remote + a read-only deploy key
# (git@github.com:maczeo11/loan-doc-processing-agent.git) so scheduled/CI
# deploys can `git fetch` a private repo without a password prompt - that key
# is set up separately (see docs/deployment_guide.md), not by this script,
# since a fresh box has no key yet. HTTPS above is just the initial-clone
# fallback; switch the remote to SSH once the deploy key exists.
BRANCH="${BRANCH:-main}"
APP_USER="${APP_USER:-finscan}"

echo "=================================================================="
echo "FinScan AI: EC2 Bootstrap Starting"
echo "Target Directory: ${APP_DIR}"
echo "Repository:       ${REPO_URL}"
echo "Branch:           ${BRANCH}"
echo "=================================================================="

# 1. Detect OS and install system packages
echo "[1/7] Installing system packages (Docker, Git, Curl, JQ, build tools, OCR)..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y --no-install-recommends \
        git curl jq ca-certificates gnupg lsb-release software-properties-common \
        build-essential tesseract-ocr tesseract-ocr-eng

    # Install official Docker if not present (used ONLY for db/redis/caddy now)
    if ! command -v docker >/dev/null 2>&1; then
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update -y
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    fi

    # Python 3.11 via deadsnakes - matches python:3.11-slim (what every pinned
    # dependency in requirements.txt was actually tested against), regardless
    # of whichever Python version this Ubuntu release ships natively.
    if ! command -v python3.11 >/dev/null 2>&1; then
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt-get update -y
        sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
    fi

    # Node 20 - matches node:20-slim (the ui-builder stage's base image)
    if ! command -v node >/dev/null 2>&1 || ! node --version | grep -q '^v20\.'; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf update -y
    sudo dnf install -y git curl jq docker python3.11 nodejs
elif command -v yum >/dev/null 2>&1; then
    sudo yum update -y
    sudo yum install -y git curl jq docker python3.11 nodejs
else
    echo "ERROR: Unsupported package manager. Please install Docker, Python 3.11, and Node 20 manually." >&2
    exit 1
fi

# 2. Enable & start Docker service
echo "[2/7] Enabling and starting Docker daemon..."
sudo systemctl enable --now docker

# Add current user to docker group
CURRENT_USER=$(id -un)
sudo usermod -aG docker "${CURRENT_USER}" || true

# 3. Create non-root application user (NOTE: the systemd units run as
# CURRENT_USER, e.g. `ubuntu` - not this account - since that user already
# owns the app directory end-to-end via git/SSH/sudo; see
# docs/deployment_guide.md's "known simplifications" section)
echo "[3/7] Setting up secure application directory at ${APP_DIR}..."
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
    sudo useradd -r -s /usr/sbin/nologin -d "${APP_DIR}" "${APP_USER}" || sudo useradd -r -s /bin/false -d "${APP_DIR}" "${APP_USER}"
fi

sudo mkdir -p "${APP_DIR}"
sudo chown -R "${CURRENT_USER}:docker" "${APP_DIR}"
sudo chmod 750 "${APP_DIR}"

# 4. Clone or update codebase
echo "[4/7] Checking out application repository..."
if [ -d "${APP_DIR}/app/.git" ]; then
    echo "  Existing repository detected. Fetching latest changes..."
    cd "${APP_DIR}/app"
    git fetch origin "${BRANCH}"
    git checkout "${BRANCH}"
    git pull origin "${BRANCH}"
else
    echo "  Cloning repository into ${APP_DIR}/app..."
    git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}/app"
    cd "${APP_DIR}/app"
fi

# 5. Environment configuration
echo "[5/7] Checking production environment settings..."
if [ ! -f "${APP_DIR}/app/.env" ]; then
    if [ -f "${APP_DIR}/app/.env.production.example" ]; then
        cp "${APP_DIR}/app/.env.production.example" "${APP_DIR}/app/.env"
        echo "  Created .env from .env.production.example. Note: fill in real secrets before production traffic!"
    elif [ -f "${APP_DIR}/app/.env.example" ]; then
        cp "${APP_DIR}/app/.env.example" "${APP_DIR}/app/.env"
        echo "  Created .env from .env.example. Note: Update secret keys before production traffic!"
    else
        touch "${APP_DIR}/app/.env"
    fi
fi

# Apply version stamp
chmod +x "${APP_DIR}/app/infra/version.sh" 2>/dev/null || true
"${APP_DIR}/app/infra/version.sh" --env "${APP_DIR}/app/.env"

# Secure permissions on .env
chmod 600 "${APP_DIR}/app/.env"

# 6. Build the venv + UI, install (but do not start) the systemd units.
# First real start happens via ./infra/deploy.sh so .env has a chance to be
# filled in with real secrets first.
echo "[6/7] Building Python venv, UI, and installing systemd units..."
chmod +x "${APP_DIR}/app/infra/setup_venv.sh"
"${APP_DIR}/app/infra/setup_venv.sh"

sudo cp "${APP_DIR}/app/infra/systemd/finscan-api.service" /etc/systemd/system/
sudo cp "${APP_DIR}/app/infra/systemd/finscan-worker.service" /etc/systemd/system/
sudo cp "${APP_DIR}/app/infra/systemd/finscan-outbox-dispatcher.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable finscan-api finscan-worker finscan-outbox-dispatcher

# 7. Passwordless sudo check - infra/deploy.sh calls `sudo systemctl restart
# finscan-*` non-interactively (e.g. via a future CI SSM RunShellScript call),
# so this must not prompt for a password.
echo "[7/7] Verifying passwordless sudo for deploy..."
if sudo -n true 2>/dev/null; then
    echo "  OK - ${CURRENT_USER} already has passwordless sudo."
else
    echo "  Adding a scoped passwordless-sudo rule for deploy commands..."
    echo "${CURRENT_USER} ALL=(root) NOPASSWD: /bin/systemctl restart finscan-api, /bin/systemctl restart finscan-worker, /bin/systemctl restart finscan-outbox-dispatcher, /bin/systemctl status finscan-*" \
        | sudo tee /etc/sudoers.d/finscan-deploy > /dev/null
    sudo chmod 440 /etc/sudoers.d/finscan-deploy
    sudo visudo -c
fi

echo "=================================================================="
echo "FinScan AI: EC2 Bootstrap Completed Successfully!"
echo "Fill in real secrets in ${APP_DIR}/app/.env, then deploy with:"
echo "  cd ${APP_DIR}/app && ./infra/deploy.sh"
echo "=================================================================="
