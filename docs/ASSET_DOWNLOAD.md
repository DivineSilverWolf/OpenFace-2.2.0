# Downloading OpenFace Windows assets (models + OpenCV DLLs)

**Чеклист проверок на Windows (диплом / реинжиниринг):** [WINDOWS_VERIFICATION.md](WINDOWS_VERIFICATION.md). Карта всех тестов: **[tests/README.md](../tests/README.md)**.

The repository root scripts **`download_models.ps1`** and **`download_libraries.ps1`** fetch large binaries that are not stored in git. They use **`Invoke-WebRequest`** with **retries**, **timeouts**, and **progress-style logging**.

Shared logic lives in **`tools/asset-download/OpenFaceAssetDownload.ps1`** (dot-sourced by both scripts).

## Quick start (default: Dropbox then OneDrive)

From the repository root in **PowerShell** (Windows PowerShell 5.1+ or PowerShell 7+):

```powershell
Set-Location C:\path\to\OpenFace-2.2.0
.\download_models.ps1
.\download_libraries.ps1
```

Existing files are **skipped** (same behaviour as the legacy scripts).

## Mirror / fork (GitHub Releases or any HTTPS base URL)

If Dropbox or OneDrive is slow or blocked, publish the **same bytes** on a release (or static URL tree) you control, then point the scripts at a **folder URL** where each asset is available under a **known file name**.

### Parameter or environment variable

- **`-MirrorBaseUrl`** — preferred on the command line.
- **`OPENFACE_MIRROR_BASE_URL`** — used when `-MirrorBaseUrl` is omitted (e.g. in CI or persistent shell profile).

Example:

```powershell
$env:OPENFACE_MIRROR_BASE_URL = "https://github.com/ORG/OpenFace-2.2.0/releases/download/openface-assets-v1/"
.\download_models.ps1
.\download_libraries.ps1
```

Or:

```powershell
.\download_models.ps1 -MirrorBaseUrl "https://github.com/ORG/OpenFace-2.2.0/releases/download/openface-assets-v1/"
```

The base URL should end with `/` or without it; both work.

### Order of sources

For each file, the scripts try **in order**:

1. **Mirror** — only if `MirrorBaseUrl` / `OPENFACE_MIRROR_BASE_URL` is set.  
2. **Dropbox** — original upstream links (`?dl=1` where applicable).  
3. **OneDrive** — original upstream links.

The first successful download wins.

### Mirror file names (must match exactly)

**Models** (`download_models.ps1`):

| Mirror URL leaf (appended to base) | Installed relative path |
|-----------------------------------|-------------------------|
| `cen_patches_0.25_of.dat` | `lib/local/LandmarkDetector/model/patch_experts/cen_patches_0.25_of.dat` (or without `lib/` when building from binaries layout — script keeps legacy rules) |
| `cen_patches_0.35_of.dat` | … `cen_patches_0.35_of.dat` |
| `cen_patches_0.50_of.dat` | … `cen_patches_0.50_of.dat` |
| `cen_patches_1.00_of.dat` | … `cen_patches_1.00_of.dat` |

**Libraries** (`download_libraries.ps1`):

| Mirror URL leaf | Installed path |
|-----------------|----------------|
| `opencv_ffmpeg410_64.dll` | `lib/3rdParty/OpenCV/bin/opencv_ffmpeg410_64.dll` |
| `opencv_world410_x64_Release.dll` | `lib/3rdParty/OpenCV/x64/v141/bin/Release/opencv_world410.dll` |
| `opencv_world410_x64_Debug.dll` | `lib/3rdParty/OpenCV/x64/v141/bin/Debug/opencv_world410d.dll` |
| `opencv_ffmpeg410.dll` | `lib/3rdParty/OpenCV/bin/opencv_ffmpeg410.dll` |
| `opencv_world410_x86_Release.dll` | `lib/3rdParty/OpenCV/x86/v141/bin/Release/opencv_world410.dll` |
| `opencv_world410_x86_Debug.dll` | `lib/3rdParty/OpenCV/x86/v141/bin/Debug/opencv_world410d.dll` |

**Why different names for `opencv_world410*.dll` on the mirror:** x64 and x86 builds share the same **on-disk** filename in different directories, but a flat release folder needs **unique** asset names. After download, the script still writes to the **original** path and filename expected by the Visual Studio layout.

### Publishing on GitHub Releases (typical)

1. Create a **tag** (e.g. `openface-assets-v1`) or use `latest` with a dedicated release name.  
2. Upload the files above as **release binary attachments** with the exact mirror leaf names.  
3. Copy the browser URL of the release asset folder (or each file’s URL without the filename and use as base + leaf as documented).  
   Example file URL:  
   `https://github.com/ORG/REPO/releases/download/openface-assets-v1/cen_patches_0.25_of.dat`  
   Base:  
   `https://github.com/ORG/REPO/releases/download/openface-assets-v1/`

## Retries and timeouts

Optional parameters (both scripts):

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `-MaxRetriesPerUri` | `5` | Attempts **per URL** before moving to Dropbox / OneDrive. |
| `-TimeoutSec` | `120` | `Invoke-WebRequest` timeout per attempt (seconds). |

## Logging

Each attempt prints a timestamped line (`[try n/N]`, URL, then `[ok]` or warnings). Skips are printed as `[skip]` when the destination file already exists.

## Tests (no network)

URL-join helpers are covered by a small script that exits non-zero on failure:

```powershell
pwsh -NoProfile -File .\tests\asset_download_uri.tests.ps1
# or Windows PowerShell:
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\asset_download_uri.tests.ps1
```

**AST parse** (no execution) for the download scripts and the shared helper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_parse.tests.ps1
```

## Integration test (network required)

Prefer running **AST parse** first (fast): `tests/download_assets_parse.tests.ps1` (see above).

To verify **`download_models.ps1`** and **`download_libraries.ps1`** end-to-end against real URLs, use the isolated workspace under **`tests/download_assets_integration/workdir/`** (created fresh each run, **gitignored**):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1
```

Details and options: **`tests/download_assets_integration/README.md`**.

Expect **several minutes** and **hundreds of MB** traffic (models from Dropbox). The script is **not** part of Linux Docker CI by default.

## Behaviour vs legacy scripts

- Same **destination paths** and **Dropbox / OneDrive URLs** as before.  
- **Mirror** is optional and tried first.  
- **Dropbox** links for `opencv_world410*.dll` are active again as middle fallback (they were commented in the legacy `download_libraries.ps1` but remain valid upstream mirrors when OneDrive fails).  
- Requires **PowerShell 5.1+** for `-TimeoutSec` on `Invoke-WebRequest` (Windows 10+ / Server 2016+ typical).
