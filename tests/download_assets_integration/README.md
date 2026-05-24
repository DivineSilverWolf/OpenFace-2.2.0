# Integration tests: `download_models.ps1` / `download_libraries.ps1`

These tests download **real** assets from Dropbox/OneDrive (or your mirror) into an isolated **`workdir/`** under this folder. **`workdir/` is gitignored.**

## Requirements

- Windows, **PowerShell 5.1+**
- Network access to Dropbox and/or OneDrive
- Enough free disk space (~hundreds of MB for all models + DLLs)

## Quick checks (no big downloads)

From repo root, AST-parse the scripts and run URI unit tests:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_parse.tests.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\asset_download_uri.tests.ps1
```

## Run

From **repository root**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1
```

Optional (faster fail / smaller retries during debugging):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1 -MaxRetriesPerUri 2 -TimeoutSec 90
```

With a fork mirror (tried first):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\download_assets_integration\Run-DownloadAssetsIntegration.ps1 -MirrorBaseUrl "https://github.com/ORG/REPO/releases/download/tag/"
```

## What it does

1. Recreates `tests/download_assets_integration/workdir/` with a minimal `lib/` tree (same layout the scripts expect when `lib` exists).
2. Sets location to `workdir` and invokes the repo-root scripts with **absolute** `-File` paths (so `$PSScriptRoot` inside the scripts still points at the real repo root for dot-sourcing helpers).
3. Asserts each expected file exists and is larger than a minimum size (rejects HTML error stubs). Models use **500 KB** minimum; OpenCV DLLs in this tree are **~100 KB**, so the test uses **80 KB** minimum for DLLs (not multi-megabyte `opencv_world` builds).

## Cleanup

Delete `workdir/` manually, or run the script again (it removes `workdir` before each run).

## Logs for a thesis / report

Redirect console output to the repo-root **`log/`** directory (gitignored except `log/README.md`); see **[WINDOWS_VERIFICATION.md](../../docs/WINDOWS_VERIFICATION.md)** for `Tee-Object` examples and **[tests/README.md](../README.md)** for the full test map.
