# Tests and static checks (this fork)

| What | Where | CI (Linux) | Windows (local) |
|------|-------|------------|-----------------|
| vcpkg manifest, presets, `log/`, no vendored `FindBLAS` | `tests/vcpkg_manifest_validate.py` | yes (`native-manifest-presets`) | `python tests/vcpkg_manifest_validate.py` |
| Windows **native vcpkg proof** workflow wiring | `tests/test_workflow_windows_native_vcpkg_proof.py` | yes | same |
| Smoke compare path rules | `tests/test_compare_smoke_of_details_paths.py` | yes | same |
| LSL streamer CLI | `tests/test_lsl_streamer.py` | yes | same |
| BIDS derivatives export | `tests/test_of2bids.py` | yes | same |
| PowerShell: AST parse of download scripts | `tests/download_assets_parse.tests.ps1` | no (by design) | [WINDOWS_VERIFICATION.md](../docs/WINDOWS_VERIFICATION.md) |
| PowerShell: URI helpers | `tests/asset_download_uri.tests.ps1` | no | same |
| PowerShell: **network** download integration | `tests/download_assets_integration/` | no | same |

Docker smoke + baseline compare: `.github/workflows/ci.yml` → `tools/run_smoke_and_compare.sh` (see [BASELINE_AND_REGRESSION.md](../docs/BASELINE_AND_REGRESSION.md)).

Capture-only workflow for refreshing git baseline: `.github/workflows/smoke-baseline-artifact.yml` (manual).
