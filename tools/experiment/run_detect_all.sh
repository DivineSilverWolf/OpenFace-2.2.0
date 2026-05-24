#!/usr/bin/env bash
# Run eye-transition detection on all Experiment/*.mp4 outputs and write comparison report.
set -euo pipefail
export PATH="/usr/bin:/bin:/usr/local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
EXP="${REPO_ROOT}/Experiment"
TOL_SEC="${TOLERANCE_SEC:-5}"

for csv in "${EXP}"/Co_Sin_001_*/Co_Sin_001_*.csv; do
  [[ -f "${csv}" ]] || continue
  echo "=== detect: ${csv} ==="
  python3 "${SCRIPT_DIR}/detect_eye_transitions.py" "${csv}"
done

python3 "${SCRIPT_DIR}/compare_eye_transitions.py" \
  --experiment-dir "${EXP}" \
  --tolerance-sec "${TOL_SEC}" \
  --report "${EXP}/REPORT.md"

echo "Done. See ${EXP}/REPORT.md (tolerance |Δt| <= ${TOL_SEC} s)"
