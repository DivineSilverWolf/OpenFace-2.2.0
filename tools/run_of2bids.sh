#!/usr/bin/env bash
# Run of2bids with PYTHONPATH set to repo tools/ (Linux/macOS/WSL).
# Usage: ./tools/run_of2bids.sh --bids-root /path/to/bids --subject 01 --task rest ...
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/tools"
cd "${ROOT}"
exec python -m of2bids "$@"
