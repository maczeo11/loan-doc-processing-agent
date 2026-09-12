#!/usr/bin/env bash
# ==============================================================================
# FinScan AI: Native venv + UI build (replaces the Docker image build for the
# api/worker/outbox-dispatcher services under the systemd-native deploy model).
# Idempotent - safe to run on every deploy: creates the venv only if missing,
# and pip/npm's own caches make a no-op reinstall fast when nothing changed.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV="${ROOT_DIR}/.venv"
PYTHON_BIN="${FINSCAN_PYTHON_BIN:-python3.11}"

echo "[setup_venv] Using Python: $(${PYTHON_BIN} --version 2>&1)"

if [ ! -d "${VENV}" ]; then
    echo "[setup_venv] Creating venv at ${VENV}..."
    "${PYTHON_BIN}" -m venv "${VENV}"
fi

"${VENV}/bin/pip" install --upgrade pip

# CPU-only torch FIRST, from PyTorch's own wheel index - matches
# infra/Dockerfile.api's approach exactly (applied uniformly here regardless
# of api vs worker, fixing infra/Dockerfile.worker's pre-existing gap where it
# never did this step). Without this, `ragas` -> `sentence-transformers`'s
# transitive torch dependency pulls the full CUDA build later during the
# requirements.txt install, which blew disk before.
echo "[setup_venv] Installing CPU-only torch..."
"${VENV}/bin/pip" install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

echo "[setup_venv] Installing requirements.txt..."
"${VENV}/bin/pip" install --no-cache-dir --default-timeout=1000 --retries 5 -r "${ROOT_DIR}/requirements.txt"

echo "[setup_venv] Installing project (editable)..."
"${VENV}/bin/pip" install --no-cache-dir -e "${ROOT_DIR}"

echo "[setup_venv] Building React UI..."
pushd "${ROOT_DIR}/apps/ui" > /dev/null
npm ci
npm run build
popd > /dev/null

echo "[setup_venv] Done."
