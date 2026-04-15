#!/usr/bin/env bash
# One-time (or explicit) copy: smoke_test/output -> smoke_test/baseline_output
# Use after a golden smoke run; do not use as part of every CI compare.
set -euo pipefail

export PATH="/usr/bin:/bin:/usr/local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SMOKE_DIR="${REPO_ROOT}/smoke_test"
SRC="${SRC:-${SMOKE_DIR}/output}"
DST="${DST:-${SMOKE_DIR}/baseline_output}"
FORCE="${FORCE:-0}"

if [[ ! -d "${SRC}" ]]; then
  echo "ERROR: source missing: ${SRC}" >&2
  exit 1
fi

if ! find "${SRC}" -type f \( -name "*.csv" -o -name "*.hog" -o -name "*_of_details.txt" \) -print -quit 2>/dev/null | grep -q .; then
  echo "ERROR: no regression artifacts under ${SRC} (.csv / .hog / *_of_details.txt)." >&2
  exit 1
fi

if [[ -d "${DST}" ]] && [[ -n "$(find "${DST}" -type f \( -name "*.csv" -o -name "*.hog" \) -print -quit 2>/dev/null)" ]] && [[ "${FORCE}" != "1" ]]; then
  echo "ERROR: ${DST} already contains baseline-like files. Set FORCE=1 to overwrite, or remove ${DST}." >&2
  exit 1
fi

if [[ "${FORCE}" == "1" ]] && [[ -d "${DST}" ]]; then
  rm -rf "${DST}"
fi
mkdir -p "${DST}"
cp -a "${SRC}/." "${DST}/"
echo "Baseline snapshot written to: ${DST}"
echo "Next: run ./tools/run_smoke_and_compare.sh (output/ will be cleaned and regenerated; compare uses baseline_output/)."
