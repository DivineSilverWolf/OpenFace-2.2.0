#!/usr/bin/env bash
# Recreate OpenFace container with a Docker-safe DATA_MOUNT (same as run_smoke.sh).
# Use this instead of raw "docker compose up" when DATA_MOUNT may be a Windows path
# (e.g. PowerShell expanded $(pwd) before bash saw the command).
set -euo pipefail

export PATH="/usr/bin:/bin:/usr/local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SMOKE_DIR="${REPO_ROOT}/smoke_test"

# shellcheck source=smoke_data_mount.sh
source "${SCRIPT_DIR}/smoke_data_mount.sh"
openface_normalize_data_mount "${SMOKE_DIR}"

export DOCKERUSER="${DOCKERUSER:-local}"
export DOCKERTAG="${DOCKERTAG:-2.2.0}"
export DATA_MOUNT

cd "${REPO_ROOT}"
echo "Using DATA_MOUNT=${DATA_MOUNT}" >&2
docker compose up -d --force-recreate openface
