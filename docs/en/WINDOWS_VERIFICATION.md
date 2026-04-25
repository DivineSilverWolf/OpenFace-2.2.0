# Windows: verification for thesis / reengineering

A compact checklist of what can be shown **reproducibly** on Windows: asset download scripts and native vcpkg-based build flow.

## 1. Download scripts (PowerShell)

### Fast, offline (AST syntax check only)

From the **repository root**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_parse.tests.ps1
```

### URI logic (no large downloads)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\asset_download_uri.tests.ps1
```

### Full integration (network, large files)

Downloads real `cen_patches_*.dat` (tens/hundreds of MB) and OpenCV DLLs into isolated **`tests/download_assets_integration/workdir/`** (gitignored).

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1
```

Expect **several minutes** and **hundreds of MB** of traffic. For debugging, reduce retries and timeout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1 -MaxRetriesPerUri 2 -TimeoutSec 90
```

Details: **`tests/download_assets_integration/README.md`**; mirror documentation: **[ASSET_DOWNLOAD.md](ASSET_DOWNLOAD.md)**.

### Log files for thesis appendix

Use the root **`log/`** directory: only **`log/README.md`** is tracked, everything else under `log/` is gitignored. Put logs there to keep the root clean and avoid accidental commits.

```powershell
New-Item -ItemType Directory -Force -Path .\log | Out-Null
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_parse.tests.ps1 2>&1 | Tee-Object -FilePath .\log\parse_tests.log
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1 2>&1 | Tee-Object -FilePath .\log\integration_download.log
```

You can rename `parse_tests.log` / `integration_download.log`; for thesis appendix use raw files from **`log/`** (they should not be committed).

## 2. Native Windows build + vcpkg (CMake Presets)

Local instructions: **[NATIVE_BUILD_VCPKG.md](NATIVE_BUILD_VCPKG.md)** (`cmake --preset windows-msvc-vcpkg`, `VCPKG_ROOT`, first configure can be long).

On GitHub: workflow **Windows native vcpkg proof** supports manual run and auto-run on `push` to `reengineering` when paths from that doc change. After build, it runs the **same Python checks** as Linux job `native-manifest-presets` in `ci.yml`, then runs **native smoke** (no Docker) and compare against `baseline_manifest_ci.json`.

## 3. Same gates as Docker CI, but native (PowerShell)

After successful `cmake --build --preset windows-msvc-vcpkg-release` and one-time **`download_models.ps1`**:

```powershell
# Same Python checks as Linux CI + smoke + compare (same gate contract as ci.yml / baseline_manifest_ci.json)
.\tools\windows\Run-WindowsNativeTestSuite.ps1 -WithSmoke
```

Python checks only (without OpenFace binaries):

```powershell
.\tools\windows\Run-WindowsNativeTestSuite.ps1
```

Smoke + compare only (if Python checks were already run):

```powershell
.\tools\windows\Run-NativeSmokeAndCompare.ps1
```

Short scenario note: **`tools/windows/README.md`**. Full `*.csv` / `*.hog` on Windows usually **do not match** Linux baseline; merge-CI contract is **`*_of_details.txt`** in tolerant mode (see [BASELINE_AND_REGRESSION.md](BASELINE_AND_REGRESSION.md)).

## 4. Relation to Linux CI

Docker smoke + baseline compare still live in **[BASELINE_AND_REGRESSION.md](BASELINE_AND_REGRESSION.md)** and `.github/workflows/ci.yml` as the reference Linux path. Native scripts from section 3 provide **Python parity + smoke gate parity** (`*_of_details.txt`) without running Docker Desktop on Windows.

Full map of automated tests and scripts: **[tests/README.md](../../tests/README.md)**.
