#!/usr/bin/env bash
# WSL helper: build OpenFace container, run smoke test, then compare with baseline.
set -euo pipefail

export PATH="/usr/bin:/bin:/usr/local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SMOKE_DIR="${REPO_ROOT}/smoke_test"

MODE="${MODE:-strict}"                         # strict | tolerant
ABS_TOL="${ABS_TOL:-1e-6}"                     # used in tolerant mode
BASELINE_DIR="${BASELINE_DIR:-${SMOKE_DIR}/baseline_output}"
ACTUAL_DIR="${ACTUAL_DIR:-${SMOKE_DIR}/output}"
MANIFEST="${MANIFEST:-${SMOKE_DIR}/baseline_manifest.json}"

DOCKERUSER="${DOCKERUSER:-local}"
DOCKERTAG="${DOCKERTAG:-2.2.0}"
DATA_MOUNT="${DATA_MOUNT:-${SMOKE_DIR}}"
export DOCKERUSER DOCKERTAG DATA_MOUNT

cd "${REPO_ROOT}"

# Same path normalization as run_smoke.sh (Docker volume must match docker exec paths).
if [[ "${DATA_MOUNT}" =~ ^[A-Za-z]: ]] || [[ "${DATA_MOUNT}" =~ ^[A-Za-z]:\\ ]]; then
  if command -v cygpath >/dev/null 2>&1; then
    DATA_MOUNT="$(cygpath -u "${DATA_MOUNT}")"
    export DATA_MOUNT
  elif command -v wslpath >/dev/null 2>&1; then
    DATA_MOUNT="$(wslpath -u "${DATA_MOUNT}")"
    export DATA_MOUNT
  fi
fi
if [[ -d "${DATA_MOUNT}" ]]; then
  DATA_MOUNT="$(cd "${DATA_MOUNT}" && (pwd -P 2>/dev/null || pwd))"
  export DATA_MOUNT
fi

if [[ ! -d "${BASELINE_DIR}" ]]; then
  echo "ERROR: baseline directory missing: ${BASELINE_DIR}" >&2
  echo "One-time: copy a golden smoke tree into baseline_output, e.g." >&2
  echo "  ./tools/regression/bootstrap_smoke_baseline.sh" >&2
  echo "Or: git checkout baseline -- smoke_test/baseline_output   (if tracked on branch baseline)" >&2
  exit 1
fi

if ! find "${BASELINE_DIR}" -type f -name "*.csv" -print -quit 2>/dev/null | grep -q .; then
  echo "ERROR: baseline has no *.csv under ${BASELINE_DIR}" >&2
  exit 1
fi

mkdir -p "${ACTUAL_DIR}"
BASELINE_RESOLVED="$(cd "${BASELINE_DIR}" && (pwd -P 2>/dev/null || pwd))"
ACTUAL_RESOLVED="$(cd "${ACTUAL_DIR}" && (pwd -P 2>/dev/null || pwd))"
if [[ "${ACTUAL_RESOLVED}" == "${BASELINE_RESOLVED}" ]]; then
  echo "ERROR: ACTUAL_DIR and BASELINE_DIR must differ (both resolve to ${ACTUAL_RESOLVED})." >&2
  exit 1
fi

# output/ is ONLY this run; baseline_output/ stays untouched.
echo "=== clean smoke actual output (${ACTUAL_DIR}; baseline unchanged at ${BASELINE_DIR}) ==="
rm -rf "${ACTUAL_DIR}/img" "${ACTUAL_DIR}/video"
mkdir -p "${ACTUAL_DIR}/img" "${ACTUAL_DIR}/video"

echo "=== docker compose build ==="
DOCKER_BUILDKIT=0 docker compose build

echo "=== docker compose up -d openface (recreate so volume matches DATA_MOUNT) ==="
docker compose up -d --force-recreate openface

echo "=== run smoke_test ==="
./smoke_test/run_smoke.sh

echo "=== compare smoke outputs ==="
python3 ./tools/regression/compare_smoke_outputs.py \
  --actual-dir "${ACTUAL_DIR}" \
  --baseline-dir "${BASELINE_DIR}" \
  --manifest "${MANIFEST}" \
  --mode "${MODE}" \
  --abs-tol "${ABS_TOL}"
