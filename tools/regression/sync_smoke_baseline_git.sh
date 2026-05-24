#!/usr/bin/env bash
# Populate smoke_test/baseline_output/ with only files that compare_smoke_outputs.py
# can ever compare (.csv, .hog, *_of_details.txt). Keeps repo/CI small vs copying full smoke tree.
#
# Typical flow after a golden run:
#   ./smoke_test/run_smoke.sh   # writes smoke_test/output/
#   ./tools/regression/sync_smoke_baseline_git.sh
#
# Optional: SRC=smoke_test/output (default) or an existing full baseline tree to trim.
set -euo pipefail

export PATH="/usr/bin:/bin:/usr/local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SMOKE_DIR="${REPO_ROOT}/smoke_test"
SRC="${SRC:-${SMOKE_DIR}/output}"
DST="${DST:-${SMOKE_DIR}/baseline_output}"

if [[ ! -d "${SRC}" ]]; then
  echo "ERROR: source missing: ${SRC}" >&2
  exit 1
fi

if ! find "${SRC}" -type f \( -name "*.csv" -o -name "*.hog" -o -name "*_of_details.txt" \) -print -quit 2>/dev/null | grep -q .; then
  echo "ERROR: no regression artifacts under ${SRC} (.csv / .hog / *_of_details.txt)." >&2
  exit 1
fi

rm -rf "${DST}"
mkdir -p "${DST}"

while IFS= read -r -d '' file; do
  rel="${file#"${SRC}/"}"
  parent="$(dirname "${rel}")"
  if [[ "${parent}" != "." ]]; then
    mkdir -p "${DST}/${parent}"
  fi
  cp -a "${file}" "${DST}/${rel}"
done < <(find "${SRC}" -type f \( -name "*.csv" -o -name "*.hog" -o -name "*_of_details.txt" \) -print0)

echo "Git-oriented baseline written to: ${DST}"
echo "Compared files only (paths preserved). Next: git add smoke_test/baseline_output && ./tools/run_smoke_and_compare.sh"
