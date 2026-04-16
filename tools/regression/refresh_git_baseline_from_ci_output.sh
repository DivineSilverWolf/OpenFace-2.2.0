#!/usr/bin/env bash
# Copy lean regression files from an unzipped "smoke-output-for-baseline" artifact
# (workflow: .github/workflows/smoke-baseline-artifact.yml) into smoke_test/baseline_output/.
#
# Usage (from repo root, after unzip so $DIR contains img/ and video/):
#   ./tools/regression/refresh_git_baseline_from_ci_output.sh /path/to/unzipped/dir
set -euo pipefail

export PATH="/usr/bin:/bin:/usr/local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -ne 1 ]] || [[ ! -d "$1" ]]; then
  echo "Usage: $0 /path/to/unzipped-artifact-root" >&2
  echo "  The directory must contain the same layout as smoke_test/output/ (img/, video/)." >&2
  exit 1
fi

OUT="$(cd "$1" && pwd)"
SRC="${OUT}" "${SCRIPT_DIR}/sync_smoke_baseline_git.sh"

echo ""
echo "Next: review diff, then commit:"
echo "  git add smoke_test/baseline_output && git status"
echo "Confirm CI gate (same as GitHub Actions):"
echo "  export MODE=tolerant ABS_TOL=1e-5"
echo "  export MANIFEST=\"\$(pwd)/tools/regression/baseline_manifest_ci.json\""
echo "  ./tools/run_smoke_and_compare.sh"
