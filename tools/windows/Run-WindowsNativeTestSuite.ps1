#requires -Version 5.1
<#
.SYNOPSIS
  Windows-native parity checks mirroring the Linux CI jobs in .github/workflows/ci.yml (without Docker).

.DESCRIPTION
  Runs, in order:
  1) python tests/vcpkg_manifest_validate.py
  2) unittest groups: test_workflow*, test_compare_smoke*, test_lsl_streamer*
  3) tests.test_of2bids (PYTHONPATH=tools)
  Optional:
  -WithSmoke runs tools/windows/Run-NativeSmokeAndCompare.ps1 (requires a completed CMake preset build).

.PARAMETER RepoRoot
  Repository root. Default: two levels above this script.

.PARAMETER WithSmoke
  After Python checks, run native smoke + baseline compare (needs Release or Debug exes under build/windows-msvc-vcpkg).

.PARAMETER SmokeBuildDir
  Passed through as -BuildDir to Run-NativeSmokeAndCompare.ps1 (default: <RepoRoot>\\build\\windows-msvc-vcpkg).

.PARAMETER SkipPython
  Skip static Python / unittest steps (only useful with -WithSmoke for a quick re-run).
#>
param(
    [Parameter(Mandatory = $false)]
    [string]$RepoRoot = "",
    [switch]$WithSmoke,
    [Parameter(Mandatory = $false)]
    [string]$SmokeBuildDir = "",
    [switch]$SkipPython
)

$ErrorActionPreference = "Stop"

function Resolve-PythonCommand {
    foreach ($name in @("python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($null -ne $cmd) {
            return $name
        }
    }
    throw "Neither 'python' nor 'python3' found on PATH."
}

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$py = Resolve-PythonCommand

if (-not $SkipPython) {
    Push-Location $RepoRoot
    try {
        Write-Host "=== vcpkg_manifest_validate.py ==="
        & $py (Join-Path $RepoRoot "tests\vcpkg_manifest_validate.py")
        if ($LASTEXITCODE -ne 0) {
            throw "vcpkg_manifest_validate.py failed ($LASTEXITCODE)"
        }

        Write-Host "=== unittest test_workflow* ==="
        & $py -m unittest discover -s tests -p "test_workflow*.py" -v
        if ($LASTEXITCODE -ne 0) {
            throw "unittest test_workflow* failed ($LASTEXITCODE)"
        }

        Write-Host "=== unittest test_compare_smoke* ==="
        & $py -m unittest discover -s tests -p "test_compare_smoke*.py" -v
        if ($LASTEXITCODE -ne 0) {
            throw "unittest test_compare_smoke* failed ($LASTEXITCODE)"
        }

        Write-Host "=== unittest test_lsl_streamer* ==="
        & $py -m unittest discover -s tests -p "test_lsl_streamer*.py" -v
        if ($LASTEXITCODE -ne 0) {
            throw "unittest test_lsl_streamer* failed ($LASTEXITCODE)"
        }

        Write-Host "=== unittest tests.test_of2bids ==="
        $env:PYTHONPATH = (Join-Path $RepoRoot "tools")
        & $py -m unittest tests.test_of2bids -v
        if ($LASTEXITCODE -ne 0) {
            throw "tests.test_of2bids failed ($LASTEXITCODE)"
        }
    }
    finally {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
        Pop-Location
    }
}

if ($WithSmoke) {
    $smokeScript = Join-Path $PSScriptRoot "Run-NativeSmokeAndCompare.ps1"
    $smokeArgs = @{ RepoRoot = $RepoRoot }
    if (-not [string]::IsNullOrWhiteSpace($SmokeBuildDir)) {
        $smokeArgs["BuildDir"] = $SmokeBuildDir
    }
    Write-Host "=== Run-NativeSmokeAndCompare.ps1 ==="
    & $smokeScript @smokeArgs
}

Write-Host "Run-WindowsNativeTestSuite.ps1 finished successfully."
