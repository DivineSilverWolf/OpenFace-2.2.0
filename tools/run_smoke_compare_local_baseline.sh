#!/usr/bin/env bash
# Full smoke pipeline + regression compare against **machine-local** golden
# (smoke_test/baseline_output_local/), not the CI-lean tree in baseline_output/.
#
# Typical: keep baseline_output/ in sync with git (ubuntu-latest capture);
# refresh baseline_output_local/ after a golden run on your hardware:
#   SRC=smoke_test/output DST=smoke_test/baseline_output_local ./tools/regression/sync_smoke_baseline_git.sh
#
# Usage (from repo root, WSL):
#   ./tools/run_smoke_compare_local_baseline.sh
# Optional overrides (same as run_smoke_and_compare.sh):
#   MODE=tolerant ABS_TOL=1e-6 MANIFEST=./smoke_test/baseline_manifest.json ./tools/run_smoke_compare_local_baseline.sh
set -euo pipefail

export PATH="/usr/bin:/bin:/usr/local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export BASELINE_DIR="${BASELINE_DIR:-${REPO_ROOT}/smoke_test/baseline_output_local}"
export MANIFEST="${MANIFEST:-${REPO_ROOT}/smoke_test/baseline_manifest.json}"
export MODE="${MODE:-tolerant}"
export ABS_TOL="${ABS_TOL:-1e-6}"

if [[ ! -d "${BASELINE_DIR}" ]] || ! find "${BASELINE_DIR}" -type f -name "*.csv" -print -quit 2>/dev/null | grep -q .; then
  echo "ERROR: local baseline missing or empty: ${BASELINE_DIR}" >&2
  echo "Populate from a golden smoke run, e.g." >&2
  echo "  SRC=${REPO_ROOT}/smoke_test/output DST=${REPO_ROOT}/smoke_test/baseline_output_local ${REPO_ROOT}/tools/regression/sync_smoke_baseline_git.sh" >&2
  exit 1
fi

exec "${SCRIPT_DIR}/run_smoke_and_compare.sh"
