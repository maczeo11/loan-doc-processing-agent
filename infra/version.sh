#!/usr/bin/env bash
# ==============================================================================
# FinScan AI: Release Version & Build Stamping Utility
# Derives Git SHA, UTC build timestamp, and optional semantic release tag.
# ==============================================================================

set -euo pipefail

# 1. Derive Git SHA (short 7-char hash)
if git rev-parse --git-dir > /dev/null 2>&1; then
    GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
else
    GIT_SHA="${GIT_SHA:-unknown}"
fi

# 2. Derive UTC build timestamp in ISO 8601 format
BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# 3. Derive semantic release tag if present, else fallback to env or 1.0.0
if git rev-parse --git-dir > /dev/null 2>&1; then
    SEMVER_TAG=$(git describe --tags --exact-match 2>/dev/null || git describe --tags --abbrev=0 2>/dev/null || echo "1.0.0")
else
    SEMVER_TAG="${RELEASE_VERSION:-1.0.0}"
fi

# Mode handling
MODE="${1:-print}"

case "${MODE}" in
    --json)
        cat <<EOF
{
  "version": "${SEMVER_TAG}",
  "git_sha": "${GIT_SHA}",
  "build_timestamp": "${BUILD_TIMESTAMP}"
}
EOF
        ;;
    --env)
        TARGET_ENV="${2:-.env}"
        echo "[version.sh] Stamping version into ${TARGET_ENV}..."
        # Update or append RELEASE_VERSION, GIT_SHA, BUILD_TIMESTAMP
        if [ -f "${TARGET_ENV}" ]; then
            sed -i.bak '/^RELEASE_VERSION=/d' "${TARGET_ENV}" 2>/dev/null || true
            sed -i.bak '/^GIT_SHA=/d' "${TARGET_ENV}" 2>/dev/null || true
            sed -i.bak '/^BUILD_TIMESTAMP=/d' "${TARGET_ENV}" 2>/dev/null || true
            rm -f "${TARGET_ENV}.bak" 2>/dev/null || true
        fi
        cat <<EOF >> "${TARGET_ENV}"
RELEASE_VERSION="${SEMVER_TAG}"
GIT_SHA="${GIT_SHA}"
BUILD_TIMESTAMP="${BUILD_TIMESTAMP}"
EOF
        echo "[version.sh] Version stamp applied: version=${SEMVER_TAG}, sha=${GIT_SHA}, ts=${BUILD_TIMESTAMP}"
        ;;
    --export)
        echo "export RELEASE_VERSION="${SEMVER_TAG}""
        echo "export GIT_SHA="${GIT_SHA}""
        echo "export BUILD_TIMESTAMP="${BUILD_TIMESTAMP}""
        ;;
    print|*)
        echo "VERSION=${SEMVER_TAG}"
        echo "GIT_SHA=${GIT_SHA}"
        echo "BUILD_TIMESTAMP=${BUILD_TIMESTAMP}"
        ;;
esac
