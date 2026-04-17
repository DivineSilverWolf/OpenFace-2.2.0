# Windows 11 + WSL2 smoke/regression quick setup

For **native Windows builds** (declarative deps via vcpkg + CMake presets, without the historical DLL download scripts), see [NATIVE_BUILD_VCPKG.md](NATIVE_BUILD_VCPKG.md). The flow below is the **Docker** path (same environment as CI smoke).

Use these commands from **WSL bash** in the repo root so `DATA_MOUNT` stays a Linux path that Docker accepts.

## Recommended (normalized `DATA_MOUNT` before Docker)

`./tools/smoke_docker_up.sh` applies the same Windows→Unix path rules as `run_smoke.sh`, then recreates the `openface` container. Prefer it over a bare `docker compose up` when `DATA_MOUNT` might be a `C:\...` path.

```bash
export DOCKERUSER=local
export DOCKERTAG=2.2.0
export DATA_MOUNT="$(pwd)/smoke_test"
./tools/smoke_docker_up.sh
./smoke_test/run_smoke.sh
./tools/regression/bootstrap_smoke_baseline.sh
./tools/run_smoke_and_compare.sh
```

## `DATA_MOUNT`: bash vs Windows-style paths

Shared logic lives in `tools/smoke_data_mount.sh` (sourced from `smoke_test/run_smoke.sh` and `tools/run_smoke_and_compare.sh`).

- **WSL / Linux**: `export DATA_MOUNT="$(pwd)/smoke_test"` is enough.
- **Windows drive letter** (`C:\...`, `C:/...`, or mixed with `/smoke_test`): converted with `wslpath -u` (WSL) or `cygpath -u` (Git Bash / MSYS) when available.
- **PowerShell calling WSL**: do not let PowerShell expand `$(pwd)` inside double quotes before bash runs. Prefer either:
  - open **WSL** and run the block above; or
  - single-quote the whole `bash -lc '...'` argument so `$(pwd)` runs **inside** bash, for example:

```powershell
wsl -e bash -lc 'cd "/mnt/c/Users/YOU/path/OpenFace-2.2.0" && export DOCKERUSER=local DOCKERTAG=2.2.0 DATA_MOUNT="$(pwd)/smoke_test" && ./tools/smoke_docker_up.sh && ./smoke_test/run_smoke.sh'
```

Notes:

- Keep `DATA_MOUNT` identical for container creation and `run_smoke.sh` (or use `smoke_docker_up.sh` + defaults so they always match).
- If `run_smoke.sh` reports `DATA_MOUNT mismatch`, recreate the container, e.g. `./tools/smoke_docker_up.sh`.
