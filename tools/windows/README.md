# Windows native helpers (vcpkg / MSVC)

Scripts here support **native** OpenFace runs on Windows with the same **smoke inputs** and **CI baseline manifest** as Linux Docker CI (see `.github/workflows/ci.yml` vs `.github/workflows/windows-native-vcpkg-proof.yml`).

| Script | Purpose |
|--------|---------|
| `Ensure-NativeOpenFaceRepoLayout.ps1` | Creates repo-root junctions `model/`, `classifiers/`, `AU_predictors/` pointing into `lib/...` so exes resolve default relative paths (same idea as the Linux container layout). |
| `Remove-NativeOpenFaceRepoLayout.ps1` | Removes those junctions only (skips normal directories). |
| `Run-NativeSmokeAndCompare.ps1` | Cleans `smoke_test/output/{img,video}`, runs `FaceLandmarkImg` (×6) + `FeatureExtraction` (×2), then `tools/regression/compare_smoke_outputs.py` with `MODE` / `ABS_TOL` / `MANIFEST` env vars (defaults match Docker CI: tolerant, `1e-5`, `baseline_manifest_ci.json`). Runs `download_models.ps1` if CEN `*.dat` are missing. |
| `Run-WindowsNativeTestSuite.ps1` | Runs the same **Python** checks as Linux `native-manifest-presets` plus optional `-WithSmoke` (calls `Run-NativeSmokeAndCompare.ps1`). |

**Prerequisites:** `cmake --preset windows-msvc-vcpkg` and `cmake --build --preset windows-msvc-vcpkg-release` (or Debug) so `FaceLandmarkImg.exe` exists; `VCPKG_ROOT` during configure as in [NATIVE_BUILD_VCPKG.md](../../docs/NATIVE_BUILD_VCPKG.md).

**One-liner from repo root (after build):**

```powershell
.\tools\windows\Run-WindowsNativeTestSuite.ps1 -WithSmoke
```

Python-only (no OpenFace binaries):

```powershell
.\tools\windows\Run-WindowsNativeTestSuite.ps1
```

See [WINDOWS_VERIFICATION.md](../../docs/WINDOWS_VERIFICATION.md) and [NATIVE_BUILD_VCPKG.md](../../docs/NATIVE_BUILD_VCPKG.md).
