#!/usr/bin/env bash
# Shared DATA_MOUNT normalization for smoke + Docker bind mounts.
# Intended to be sourced from other bash scripts (no "set -euo pipefail" here).
#
# Handles:
# - unset DATA_MOUNT -> optional default directory (e.g. smoke_test/)
# - Windows paths (C:\..., C:/..., mixed with /smoke_test) -> Unix path via cygpath (Git Bash/MSYS) or wslpath (WSL)
# - existing Unix paths -> canonical absolute via cd/pwd -P
#
# Usage (after defining REPO_ROOT or passing default):
#   # shellcheck source=smoke_data_mount.sh
#   source "${REPO_ROOT}/tools/smoke_data_mount.sh"
#   openface_normalize_data_mount "${SMOKE_DIR}"

openface_normalize_data_mount() {
  local _default_dir="${1:-}"

  if [[ -z "${DATA_MOUNT:-}" ]]; then
    if [[ -n "${_default_dir}" ]]; then
      export DATA_MOUNT="${_default_dir}"
    fi
  fi

  if [[ -z "${DATA_MOUNT:-}" ]]; then
    return 0
  fi

  # Windows drive-letter path (C:\..., C:/..., c:\...)
  if [[ "${DATA_MOUNT}" =~ ^[A-Za-z]: ]] || [[ "${DATA_MOUNT}" =~ ^[A-Za-z]:\\ ]]; then
    if command -v cygpath >/dev/null 2>&1; then
      DATA_MOUNT="$(cygpath -u "${DATA_MOUNT}")"
      export DATA_MOUNT
    elif command -v wslpath >/dev/null 2>&1; then
      DATA_MOUNT="$(wslpath -u "${DATA_MOUNT}")"
      export DATA_MOUNT
    else
      echo "ERROR: DATA_MOUNT looks like a Windows path (${DATA_MOUNT}) but neither cygpath nor wslpath is available." >&2
      echo "Fix: run smoke from WSL/Git Bash, install WSL tools, or set DATA_MOUNT to a Linux-style path (e.g. /mnt/c/.../smoke_test)." >&2
      return 1
    fi
  fi

  if [[ -d "${DATA_MOUNT}" ]]; then
    DATA_MOUNT="$(cd "${DATA_MOUNT}" && (pwd -P 2>/dev/null || pwd))"
    export DATA_MOUNT
  fi

  return 0
}
