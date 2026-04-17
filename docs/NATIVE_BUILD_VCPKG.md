# Native build (vcpkg + CMake Presets) vs Docker

**Windows: скрипты скачивания + логи для диплома:** [WINDOWS_VERIFICATION.md](WINDOWS_VERIFICATION.md).

OpenFace historically used PowerShell helpers to download OpenCV and FFmpeg DLLs on Windows. For a more **declarative** dependency story (useful for thesis write-ups and reproducible dev machines), this repository includes:

- **`vcpkg.json`** — manifest-mode pins for OpenCV 4, Boost (filesystem + system), OpenBLAS, and dlib, aligned with the top-level `CMakeLists.txt` (`find_package` calls).
- **`CMakePresets.json`** — IDE-friendly presets that point CMake at the vcpkg toolchain via **`VCPKG_ROOT`**.

**Docker remains the supported reference path** for bit-identical Linux CI and the smoke baseline workflow (`docker compose build`, `DATA_MOUNT`, `./smoke_test/run_smoke.sh`). See [SETUP_WINDOWS11_WSL2.md](SETUP_WINDOWS11_WSL2.md) and the OpenFace wiki-style flow there.

Microsoft documents vcpkg + CMake integration and preset-based workflows in the official vcpkg and CMake documentation; this doc only records **how this repo wires them**.

## Prerequisites

1. **CMake** 3.21 or newer (presets), plus a generator:
   - Windows: **Visual Studio 2022** (MSVC x64), or install Ninja if you prefer a Ninja + MSVC workflow (not preset-listed here).
   - Linux / WSL: **Ninja**, a compiler (**GCC 8+** per `CMakeLists.txt`, or **Clang**), and usual build tools (`build-essential` / `clang`).
2. A **vcpkg** clone and **`VCPKG_ROOT`** pointing at it (environment variable). Example (bash):

```bash
export VCPKG_ROOT="$HOME/vcpkg"
```

If you cloned vcpkg with **`git clone --depth 1`**, the commit in **`vcpkg.json` → `builtin-baseline`** is not in the object database until you fetch it. Without that, configure fails with errors about **`versions/baseline.json`** and `git show`. Fix:

```bash
git -C "$VCPKG_ROOT" fetch origin "$(jq -r '."builtin-baseline"' vcpkg.json)"
```

(PowerShell: read `builtin-baseline` from `vcpkg.json`, then `git -C $env:VCPKG_ROOT fetch origin <sha>`.) The GitHub Actions **Windows native vcpkg proof** workflow does this fetch automatically after the shallow clone.

On Windows PowerShell:

```powershell
$env:VCPKG_ROOT = "C:\path\to\vcpkg"
```

3. **Models** still come from the asset scripts documented in [ASSET_DOWNLOAD.md](ASSET_DOWNLOAD.md); vcpkg does not replace model download.

## Quick validation (no vcpkg install)

From the repo root (CMake **3.21+** must be on `PATH` for the second part; otherwise the script skips `cmake --list-presets` with a note):

```bash
python3 tests/vcpkg_manifest_validate.py
```

This checks `vcpkg.json`, `CMakePresets.json`, and `FindOpenBLAS.cmake` guardrails, and runs `cmake --list-presets` when CMake is new enough.

## Configure and build (presets)

From the repository root:

**Windows (MSVC + vcpkg)**

```powershell
cmake --preset windows-msvc-vcpkg
cmake --build --preset windows-msvc-vcpkg-release
```

**Linux or WSL (GCC)**

```bash
cmake --preset linux-gcc
cmake --build --preset linux-gcc
```

**Linux or WSL (Clang)**

```bash
cmake --preset wsl-clang
cmake --build --preset wsl-clang
```

First configure with manifest mode may trigger a long vcpkg build of OpenCV and FFmpeg-related ports; that is expected.

### Manual equivalent (no presets)

If your CMake is older or you prefer explicit flags:

```bash
cmake -S . -B build/manual \
  -DCMAKE_TOOLCHAIN_FILE="$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" \
  -G Ninja
cmake --build build/manual
```

## BLAS / LAPACK and dlib (vcpkg + MSVC)

Do **not** put a custom **`FindBLAS.cmake`** ahead of CMake’s built-in module on `CMAKE_MODULE_PATH`. A legacy vendor copy breaks **`find_dependency(BLAS)`** inside vcpkg’s **`dlibConfig.cmake`** (CMake’s `FindBLAS` creates **`BLAS::BLAS`** since 3.18; without it, configure fails with *target "BLAS::BLAS" was not found*). This repo relies on CMake’s stock **`FindBLAS`** / **`FindLAPACK`** for dlib and for **`OpenFaceConfig.cmake.in`**.

## OpenCV components

`CMakeLists.txt` requests: `core`, `imgproc`, `calib3d`, `highgui`, `objdetect`. The manifest enables **`opencv4`** with **default port features** (including `calib3d`, `highgui`, Windows backends such as `win32ui` / `msmf` where applicable) **plus** explicit **`ffmpeg`** and image codecs (`jpeg`, `png`, `tiff`, `webp`). Do **not** set `"default-features": false` on `opencv4` unless you also re-enable every component `find_package(OpenCV … COMPONENTS …)` needs. Adjust **`vcpkg.json`** only if you intentionally need extra OpenCV features (keeping **`lib/local/**`** unchanged).

## Regression after a native rebuild

Changing the OpenCV / BLAS / compiler stack can produce **small numeric drift** in dense outputs (especially `*.csv`), while summary `*_of_details.txt` may still match within tolerance.

1. Run smoke against the same inputs as CI: `./smoke_test/run_smoke.sh` (from WSL/Linux or a shell where your native binaries and `DATA_MOUNT` are set up).
2. Compare outputs:
   - **Same gate as CI:** `./tools/run_smoke_and_compare.sh` (uses `baseline_output/` and the CI-oriented manifest by default in workflow; locally mirror `.github/workflows/ci.yml` env for `MANIFEST` / `ABS_TOL` if you want an exact match).
   - **Full tolerant regression on your machine:** `./tools/run_smoke_compare_local_baseline.sh` and/or refresh `smoke_test/baseline_output_local/` — see [BASELINE_AND_REGRESSION.md](BASELINE_AND_REGRESSION.md).

The compare tool **`tools/regression/compare_smoke_outputs.py`** already walks CSV and text as **streams of numeric tokens** with a configurable absolute tolerance (`ABS_TOL`), which is the practical approach until a dedicated column-aware CSV comparator exists.

If you **intentionally** upgrade vcpkg baseline or OpenCV and accept new numbers, refresh the appropriate baseline using `tools/regression/sync_smoke_baseline_git.sh` (git baseline) or bootstrap scripts documented in [BASELINE_AND_REGRESSION.md](BASELINE_AND_REGRESSION.md).

## GitHub Actions proof build (Windows + vcpkg)

A full native configure/build (OpenCV via vcpkg) is **slow** and is **not** part of the default Linux Docker CI.

**When it runs**

- **Automatically** on **push** to branch **`reengineering`** when any of these change: `vcpkg.json`, `CMakePresets.json`, `cmake/**`, `CMakeLists.txt`, or `.github/workflows/windows-native-vcpkg-proof.yml`.
- **Manually** any time: **Actions** → **Windows native vcpkg proof** → **Run workflow** (`workflow_dispatch`).

**Steps**

1. Open **Actions** → workflow **Windows native vcpkg proof** (`.github/workflows/windows-native-vcpkg-proof.yml`) to see runs (or trigger manually).
2. The job clones vcpkg, sets `VCPKG_ROOT`, runs `cmake --preset windows-msvc-vcpkg` and `cmake --build --preset windows-msvc-vcpkg-release`.
3. On success, download the artifact **`windows-vcpkg-proof`** (contains `CMakeCache.txt` and `bin/` with built executables when the link step completes).

Timeout is set to **360 minutes** for the first-time dependency build.

## Baseline pin (`builtin-baseline`)

`vcpkg.json` sets **`builtin-baseline`** to a tagged vcpkg registry commit (see `vcpkg.json` in the repo). To move to a newer registry snapshot, follow upstream vcpkg guidance (`vcpkg x-update-baseline`, etc.) and re-run smoke regression.

## Docker (unchanged reference)

For the reproducible container build and `DATA_MOUNT` semantics, keep using:

- `docker compose build` (from repo `docker/` layout as in CI),
- `./tools/smoke_docker_up.sh` and `./smoke_test/run_smoke.sh` as in [SETUP_WINDOWS11_WSL2.md](SETUP_WINDOWS11_WSL2.md).

Native Windows + vcpkg and Docker are **orthogonal**: choose Docker when you want the same environment as CI; choose vcpkg when you want a local MSVC toolchain without vendored DLL scripts.
