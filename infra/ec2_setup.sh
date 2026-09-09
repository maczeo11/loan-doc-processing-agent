#!/usr/bin/env bash
# ==============================================================================
# FinScan AI: EC2 Host Bootstrap & Initialization Script (Phase 7)
# Installs Docker, Compose, creates secure application directory, sets permissions,
# and starts the production stack on a single ARM64/x86 EC2 instance.
# ==============================================================================

set -euo pipefail

APP_DIR="/opt/finscan"
REPO_URL="${REPO_URL:-https://github.com/maczeo11/loan-doc-processing-agent.git}"
BRANCH="${BRANCH:-main}"
APP_USER="${APP_USER:-finscan}"

echo "=================================================================="
echo "FinScan AI: EC2 Bootstrap Starting"
echo "Target Directory: ${APP_DIR}"
echo "Repository:       ${REPO_URL}"
echo "Branch:           ${BRANCH}"
echo "=================================================================="

# 1. Detect OS and install system packages
echo "[1/5] Installing system packages (Docker, Git, Curl, JQ)..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y --no-install-recommends \
        git curl jq ca-certificates gnupg lsb-release
    
    # Install official Docker if not present
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
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf update -y
    sudo dnf install -y git curl jq docker
elif command -v yum >/dev/null 2>&1; then
    sudo yum update -y
    sudo yum install -y git curl jq docker
else
    echo "ERROR: Unsupported package manager. Please install Docker and Git manually." >&2
    exit 1
fi

# 2. Enable & start Docker service
echo "[2/5] Enabling and starting Docker daemon..."
sudo systemctl enable --now docker

# Add current user to docker group
CURRENT_USER=$(id -un)
sudo usermod -aG docker "${CURRENT_USER}" || true

# 3. Create non-root application user and secure directory
echo "[3/5] Setting up secure application directory at ${APP_DIR}..."
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
    sudo useradd -r -s /usr/sbin/nologin -d "${APP_DIR}" "${APP_USER}" || sudo useradd -r -s /bin/false -d "${APP_DIR}" "${APP_USER}"
fi

sudo mkdir -p "${APP_DIR}"
sudo chown -R "${CURRENT_USER}:docker" "${APP_DIR}"
sudo chmod 750 "${APP_DIR}"

# 4. Clone or update codebase
echo "[4/5] Checking out application repository..."
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

# 5. Environment configuration & startup
echo "[5/5] Checking production environment settings..."
if [ ! -f "${APP_DIR}/app/.env" ]; then
    if [ -f "${APP_DIR}/app/.env.example" ]; then
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

echo "=================================================================="
echo "FinScan AI: EC2 Bootstrap Completed Successfully!"
echo "To deploy or start services, run:"
echo "  cd ${APP_DIR}/app && ./infra/deploy.sh"
echo "=================================================================="
