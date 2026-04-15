#!/usr/bin/env bash
# Run OpenFace smoke tests; writes under smoke_test/output/img/img{1..6} and output/video/video{1,2}.
# Requires: Docker + compose, repo docker-compose.yml. Set DATA_MOUNT to this directory (smoke_test).
# Regression baseline for compare lives in smoke_test/baseline_output/ (not output/).
#
# Usage (from repo root, WSL):
#   export PATH="/usr/bin:/bin:/usr/local/bin:$PATH"
#   export DOCKERUSER=local DOCKERTAG=2.2.0
#   export DATA_MOUNT="$(pwd)/smoke_test"   # or realpath to smoke_test
#   DOCKER_BUILDKIT=0 docker compose build && ./tools/smoke_docker_up.sh
#   ./smoke_test/run_smoke.sh
#
# If the container was started with a different DATA_MOUNT, run: docker compose down && docker compose up -d openface

set -euo pipefail
export PATH="/usr/bin:/bin:/usr/local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SMOKE_TS="${SMOKE_TS:-2026-04-13_02-55-53}"

# shellcheck source=../tools/smoke_data_mount.sh
source "${REPO_ROOT}/tools/smoke_data_mount.sh"
if [[ -z "${DATA_MOUNT:-}" ]]; then
  echo "DATA_MOUNT not set; using ${SCRIPT_DIR}" >&2
fi
openface_normalize_data_mount "${SCRIPT_DIR}"

cd "${REPO_ROOT}"

# Fail fast if container exists with a different DATA_MOUNT than this run.
# This avoids hard-to-debug "file not found" inside docker exec.
if docker ps --format '{{.Names}}' | awk '$0=="openface"{found=1} END{exit found?0:1}'; then
  CONTAINER_DATA_MOUNT="$(docker exec openface sh -lc 'printf "%s" "${DATA_MOUNT:-}"' 2>/dev/null || true)"
  if [[ -n "${CONTAINER_DATA_MOUNT}" ]] && [[ "${CONTAINER_DATA_MOUNT}" != "${DATA_MOUNT}" ]]; then
    echo "ERROR: DATA_MOUNT mismatch." >&2
    echo "  script DATA_MOUNT:    ${DATA_MOUNT}" >&2
    echo "  container DATA_MOUNT: ${CONTAINER_DATA_MOUNT}" >&2
    echo "Recreate container with current mount:" >&2
    echo "  ./tools/smoke_docker_up.sh" >&2
    echo "  # or: docker compose up -d --force-recreate openface  (after normalizing DATA_MOUNT)" >&2
    exit 1
  fi
fi

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
