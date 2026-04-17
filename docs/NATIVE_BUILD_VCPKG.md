# Native build (vcpkg + CMake Presets) vs Docker

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

## OpenCV components

`CMakeLists.txt` requests: `core`, `imgproc`, `calib3d`, `highgui`, `objdetect`. The manifest enables **`opencv4`** with **`ffmpeg`** plus common image codecs (`jpeg`, `png`, `tiff`, `webp`). Adjust **`vcpkg.json`** only if you intentionally need extra OpenCV features (keeping **`lib/local/**`** unchanged).

## Regression after a native rebuild

Changing the OpenCV / BLAS / compiler stack can produce **small numeric drift** in dense outputs (especially `*.csv`), while summary `*_of_details.txt` may still match within tolerance.

1. Run smoke against the same inputs as CI: `./smoke_test/run_smoke.sh` (from WSL/Linux or a shell where your native binaries and `DATA_MOUNT` are set up).
2. Compare outputs:
   - **Same gate as CI:** `./tools/run_smoke_and_compare.sh` (uses `baseline_output/` and the CI-oriented manifest by default in workflow; locally mirror `.github/workflows/ci.yml` env for `MANIFEST` / `ABS_TOL` if you want an exact match).
   - **Full tolerant regression on your machine:** `./tools/run_smoke_compare_local_baseline.sh` and/or refresh `smoke_test/baseline_output_local/` — see [BASELINE_AND_REGRESSION.md](BASELINE_AND_REGRESSION.md).

The compare tool **`tools/regression/compare_smoke_outputs.py`** already walks CSV and text as **streams of numeric tokens** with a configurable absolute tolerance (`ABS_TOL`), which is the practical approach until a dedicated column-aware CSV comparator exists.

If you **intentionally** upgrade vcpkg baseline or OpenCV and accept new numbers, refresh the appropriate baseline using `tools/regression/sync_smoke_baseline_git.sh` (git baseline) or bootstrap scripts documented in [BASELINE_AND_REGRESSION.md](BASELINE_AND_REGRESSION.md).

## Baseline pin (`builtin-baseline`)

`vcpkg.json` sets **`builtin-baseline`** to a tagged vcpkg registry commit (see `vcpkg.json` in the repo). To move to a newer registry snapshot, follow upstream vcpkg guidance (`vcpkg x-update-baseline`, etc.) and re-run smoke regression.

## Docker (unchanged reference)

For the reproducible container build and `DATA_MOUNT` semantics, keep using:

- `docker compose build` (from repo `docker/` layout as in CI),
- `./tools/smoke_docker_up.sh` and `./smoke_test/run_smoke.sh` as in [SETUP_WINDOWS11_WSL2.md](SETUP_WINDOWS11_WSL2.md).

Native Windows + vcpkg and Docker are **orthogonal**: choose Docker when you want the same environment as CI; choose vcpkg when you want a local MSVC toolchain without vendored DLL scripts.
