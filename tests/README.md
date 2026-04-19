# Tests and static checks (this fork)

| What | Where | CI (Linux) | Windows (local) |
|------|-------|------------|-----------------|
| vcpkg manifest, presets, `log/`, no vendored `FindBLAS` | `tests/vcpkg_manifest_validate.py` | yes (`native-manifest-presets`) | `python tests/vcpkg_manifest_validate.py` |
| Windows **native vcpkg proof** workflow wiring | `tests/test_workflow_windows_native_vcpkg_proof.py` | yes | same |
| Smoke compare path rules | `tests/test_compare_smoke_of_details_paths.py` | yes | same |
| LSL streamer CLI | `tests/test_lsl_streamer.py` | yes | same |
| BIDS derivatives export | `tests/test_of2bids.py` | yes | same |
| **One-shot: all of the above + native smoke + CI manifest compare** | `tools/windows/Run-WindowsNativeTestSuite.ps1 -WithSmoke` | yes (`windows-native-vcpkg-proof` after MSVC build) | after `cmake --build --preset windows-msvc-vcpkg-release` and `download_models.ps1` |
| Native smoke only + compare (CI manifest) | `tools/windows/Run-NativeSmokeAndCompare.ps1` | same workflow step | same |
| PowerShell: AST parse of download scripts | `tests/download_assets_parse.tests.ps1` | no (by design) | [WINDOWS_VERIFICATION.md](../docs/WINDOWS_VERIFICATION.md) |
| PowerShell: URI helpers | `tests/asset_download_uri.tests.ps1` | no | same |
| PowerShell: **network** download integration | `tests/download_assets_integration/` | no | same |

Docker smoke + baseline compare: `.github/workflows/ci.yml` → `tools/run_smoke_and_compare.sh` (see [BASELINE_AND_REGRESSION.md](../docs/BASELINE_AND_REGRESSION.md)).

Windows native (no Docker): `.github/workflows/windows-native-vcpkg-proof.yml` → `tools/windows/Run-NativeSmokeAndCompare.ps1` (same `compare_smoke_outputs.py` + `baseline_manifest_ci.json` as Linux CI gate; see [NATIVE_BUILD_VCPKG.md](../docs/NATIVE_BUILD_VCPKG.md), [WINDOWS_VERIFICATION.md](../docs/WINDOWS_VERIFICATION.md)).

Capture-only workflow for refreshing git baseline: `.github/workflows/smoke-baseline-artifact.yml` (manual).
