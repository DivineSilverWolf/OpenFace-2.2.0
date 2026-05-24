#!/usr/bin/env bash
# Run FeatureExtraction on Experiment/*.mp4 into Experiment/<basename>/.
# Requires: openface container with DATA_MOUNT = repo root.
set -euo pipefail
export PATH="/usr/bin:/bin:/usr/local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck source=../smoke_data_mount.sh
source "${REPO_ROOT}/tools/smoke_data_mount.sh"
openface_normalize_data_mount "${REPO_ROOT}"

if ! docker ps --format '{{.Names}}' | awk '$0=="openface"{found=1} END{exit found?0:1}'; then
  echo "ERROR: openface container not running. From repo root:" >&2
  echo "  export DATA_MOUNT=\$(pwd) DOCKERUSER=local DOCKERTAG=2.2.0" >&2
  echo "  ./tools/smoke_docker_up.sh" >&2
  exit 1
fi

EXP="${DATA_MOUNT}/Experiment"
for mp4 in "${EXP}"/Co_Sin_001_*.mp4; do
  [[ -f "${mp4}" ]] || continue
  base="$(basename "${mp4}" .mp4)"
  out="${EXP}/${base}"
  mkdir -p "${out}"
  echo "=== FeatureExtraction: ${base} ==="
  # Lean CSV: 2D landmarks (eyelid geometry) + AUs (AU45 blink at transitions).
  docker exec openface FeatureExtraction \
    -f "${mp4}" \
    -out_dir "${out}" \
    -quiet \
    -2Dfp \
    -aus
done

echo "Experiment extraction finished."
