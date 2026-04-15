#!/usr/bin/env bash
# Run OpenFace smoke tests; writes under smoke_test/output/img/img{1..6} and output/video/video{1,2}.
# Requires: Docker + compose, repo docker-compose.yml. Set DATA_MOUNT to this directory (smoke_test).
# Regression baseline for compare lives in smoke_test/baseline_output/ (not output/).
#
# Usage (from repo root, WSL):
#   export PATH="/usr/bin:/bin:/usr/local/bin:$PATH"
#   export DOCKERUSER=local DOCKERTAG=2.2.0
#   export DATA_MOUNT="$(pwd)/smoke_test"   # or realpath to smoke_test
#   DOCKER_BUILDKIT=0 docker compose build && docker compose up -d openface
#   ./smoke_test/run_smoke.sh
#
# If the container was started with a different DATA_MOUNT, run: docker compose down && docker compose up -d openface

set -euo pipefail
export PATH="/usr/bin:/bin:/usr/local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SMOKE_TS="${SMOKE_TS:-2026-04-13_02-55-53}"

if [[ -z "${DATA_MOUNT:-}" ]]; then
  export DATA_MOUNT="${SCRIPT_DIR}"
  echo "DATA_MOUNT not set; using ${DATA_MOUNT}" >&2
fi

# Windows Git Bash / cmd: turn "C:\..." into a path Docker Linux can bind consistently.
if [[ "${DATA_MOUNT}" =~ ^[A-Za-z]: ]] || [[ "${DATA_MOUNT}" =~ ^[A-Za-z]:\\ ]]; then
  if command -v cygpath >/dev/null 2>&1; then
    DATA_MOUNT="$(cygpath -u "${DATA_MOUNT}")"
    export DATA_MOUNT
  elif command -v wslpath >/dev/null 2>&1; then
    DATA_MOUNT="$(wslpath -u "${DATA_MOUNT}")"
    export DATA_MOUNT
  fi
fi

# Absolute path so docker compose volume source matches paths passed to docker exec.
if [[ -d "${DATA_MOUNT}" ]]; then
  DATA_MOUNT="$(cd "${DATA_MOUNT}" && (pwd -P 2>/dev/null || pwd))"
  export DATA_MOUNT
fi

cd "${REPO_ROOT}"

for i in 1 2 3 4 5 6; do
  img_path="${DATA_MOUNT}/data/img${i}_${SMOKE_TS}.jpg"
  if [[ ! -f "${img_path}" ]]; then
    echo "ERROR: smoke input missing: ${img_path}" >&2
    echo "Set SMOKE_TS to match filenames in smoke_test/data/ (e.g. export SMOKE_TS=2026-04-13_02-55-53)." >&2
    exit 1
  fi
done
for v in 1 2; do
  vid_path="${DATA_MOUNT}/data/video${v}_${SMOKE_TS}.mp4"
  if [[ ! -f "${vid_path}" ]]; then
    echo "ERROR: smoke input missing: ${vid_path}" >&2
    echo "Set SMOKE_TS to match filenames in smoke_test/data/." >&2
    exit 1
  fi
done

for i in 1 2 3 4 5 6; do
  mkdir -p "${DATA_MOUNT}/output/img/img${i}"
done
mkdir -p "${DATA_MOUNT}/output/video/video1" "${DATA_MOUNT}/output/video/video2"

for i in 1 2 3 4 5 6; do
  echo "=== FaceLandmarkImg -> output/img/img${i} (input data/img${i}_*) ==="
  docker exec openface FaceLandmarkImg \
    -f "${DATA_MOUNT}/data/img${i}_${SMOKE_TS}.jpg" \
    -out_dir "${DATA_MOUNT}/output/img/img${i}"
done

echo "=== FeatureExtraction -> output/video/video1 (input data/video1_*) ==="
docker exec openface FeatureExtraction \
  -f "${DATA_MOUNT}/data/video1_${SMOKE_TS}.mp4" \
  -out_dir "${DATA_MOUNT}/output/video/video1"

echo "=== FeatureExtraction -> output/video/video2 (input data/video2_*) ==="
docker exec openface FeatureExtraction \
  -f "${DATA_MOUNT}/data/video2_${SMOKE_TS}.mp4" \
  -out_dir "${DATA_MOUNT}/output/video/video2"

echo "Smoke tests finished."
