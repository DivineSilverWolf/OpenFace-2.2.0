#requires -Version 5.1
<#
.SYNOPSIS
  Runs the same smoke inputs and CI-oriented baseline compare as Linux Docker CI (without Docker).

.DESCRIPTION
  - Cleans smoke_test/output/img and smoke_test/output/video (same idea as tools/run_smoke_and_compare.sh).
  - Requires CEN patch models: runs download_models.ps1 unless -SkipModelDownload and files already exist.
  - Creates repo-root junctions (model, classifiers, AU_predictors), then removes them in a finally block.

  Compare step uses tools/regression/compare_smoke_outputs.py with MANIFEST / MODE / ABS_TOL env vars
  matching .github/workflows/ci.yml (defaults: tolerant, 1e-5, baseline_manifest_ci.json).

.PARAMETER RepoRoot
  Repository root (contains smoke_test/, vcpkg.json).

.PARAMETER BuildDir
  CMake build directory (contains bin/Release and vcpkg_installed). Default: <RepoRoot>\build\windows-msvc-vcpkg

.PARAMETER SmokeTimestamp
  Timestamp suffix for smoke_test/data filenames (default matches tracked smoke media).

.PARAMETER SkipModelDownload
  Do not invoke download_models.ps1 (fail if CEN .dat files are missing).

.PARAMETER SkipCompare
  Run smoke binaries only; skip python compare (for debugging).

.PARAMETER KeepLayout
  Do not remove repo-root junctions on exit (default: remove in finally).
#>
param(
    [Parameter(Mandatory = $false)]
    [string]$RepoRoot = "",
    [Parameter(Mandatory = $false)]
    [string]$BuildDir = "",
    [Parameter(Mandatory = $false)]
    [string]$SmokeTimestamp = "2026-04-13_02-55-53",
    [switch]$SkipModelDownload,
    [switch]$SkipCompare,
    [switch]$KeepLayout
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
if ([string]::IsNullOrWhiteSpace($BuildDir)) {
    $BuildDir = Join-Path $RepoRoot "build\windows-msvc-vcpkg"
}

$binRelease = Join-Path $BuildDir "bin\Release"
$binDebug = Join-Path $BuildDir "bin\Debug"
$binDir = $null
if (Test-Path (Join-Path $binRelease "FaceLandmarkImg.exe")) {
    $binDir = $binRelease
}
elseif (Test-Path (Join-Path $binDebug "FaceLandmarkImg.exe")) {
    $binDir = $binDebug
}
else {
    throw "FaceLandmarkImg.exe not found under '$binRelease' or '$binDebug'. Build Release (or Debug) first."
}

$vcpkgHostBin = Join-Path $BuildDir "vcpkg_installed\x64-windows\bin"
if (-not (Test-Path -LiteralPath $vcpkgHostBin)) {
    throw "Missing vcpkg_installed bin (OpenCV runtime DLLs): $vcpkgHostBin"
}

$cenProbe = Join-Path $RepoRoot "lib\local\LandmarkDetector\model\patch_experts\cen_patches_0.25_of.dat"
if (-not (Test-Path -LiteralPath $cenProbe)) {
    if ($SkipModelDownload) {
        throw "CEN models missing ($cenProbe). Run download_models.ps1 or omit -SkipModelDownload."
    }
    Write-Host "=== download_models.ps1 (CEN patch experts) ==="
    & (Join-Path $RepoRoot "download_models.ps1") -MaxRetriesPerUri 5 -TimeoutSec 120
}

$manifestDefault = Join-Path $RepoRoot "tools\regression\baseline_manifest_ci.json"
$manifest = if ($env:MANIFEST) { $env:MANIFEST } else { $manifestDefault }
if (-not (Test-Path -LiteralPath $manifest)) {
    throw "Compare manifest not found: $manifest"
}
$mode = if ($env:MODE) { $env:MODE } else { "tolerant" }
$absTol = if ($env:ABS_TOL) { $env:ABS_TOL } else { "1e-5" }

$ensure = Join-Path $PSScriptRoot "Ensure-NativeOpenFaceRepoLayout.ps1"
$remove = Join-Path $PSScriptRoot "Remove-NativeOpenFaceRepoLayout.ps1"

$prevPath = $env:PATH
try {
    & $ensure -RepoRoot $RepoRoot

    $env:PATH = "$binDir;$vcpkgHostBin;$prevPath"

    $data = Join-Path $RepoRoot "smoke_test\data"
    $outRoot = Join-Path $RepoRoot "smoke_test\output"
    $imgOut = Join-Path $outRoot "img"
    $vidOut = Join-Path $outRoot "video"

    if (Test-Path -LiteralPath $imgOut) {
        Remove-Item -LiteralPath $imgOut -Recurse -Force
    }
    if (Test-Path -LiteralPath $vidOut) {
        Remove-Item -LiteralPath $vidOut -Recurse -Force
    }
    for ($i = 1; $i -le 6; $i++) {
        New-Item -ItemType Directory -Force -Path (Join-Path $imgOut "img$i") | Out-Null
    }
    New-Item -ItemType Directory -Force -Path (Join-Path $vidOut "video1"), (Join-Path $vidOut "video2") | Out-Null

    Push-Location $RepoRoot
    try {
        for ($i = 1; $i -le 6; $i++) {
            $img = Join-Path $data "img${i}_$SmokeTimestamp.jpg"
            if (-not (Test-Path -LiteralPath $img)) {
                throw "Missing smoke input: $img"
            }
            $od = Join-Path $imgOut "img$i"
            Write-Host "=== FaceLandmarkImg -> $od ==="
            & (Join-Path $binDir "FaceLandmarkImg.exe") -f $img -out_dir $od
            if ($LASTEXITCODE -ne 0) {
                throw "FaceLandmarkImg failed (exit $LASTEXITCODE) for $img"
            }
        }
        foreach ($v in @(1, 2)) {
            $vid = Join-Path $data "video${v}_$SmokeTimestamp.mp4"
            if (-not (Test-Path -LiteralPath $vid)) {
                throw "Missing smoke input: $vid"
            }
            $od = Join-Path $vidOut "video$v"
            Write-Host "=== FeatureExtraction -> $od ==="
            & (Join-Path $binDir "FeatureExtraction.exe") -f $vid -out_dir $od
            if ($LASTEXITCODE -ne 0) {
                throw "FeatureExtraction failed (exit $LASTEXITCODE) for $vid"
            }
        }
    }
    finally {
        Pop-Location
    }

    if (-not $SkipCompare) {
        $py = Resolve-PythonCommand
        $compare = Join-Path $RepoRoot "tools\regression\compare_smoke_outputs.py"
        Write-Host "=== compare_smoke_outputs.py (manifest CI gate) ==="
        & $py $compare `
            --actual-dir (Join-Path $RepoRoot "smoke_test\output") `
            --baseline-dir (Join-Path $RepoRoot "smoke_test\baseline_output") `
            --manifest $manifest `
            --mode $mode `
            --abs-tol $absTol
        if ($LASTEXITCODE -ne 0) {
            throw "compare_smoke_outputs.py failed (exit $LASTEXITCODE)"
        }
    }

    Write-Host "Native smoke + compare finished successfully."
}
finally {
    $env:PATH = $prevPath
    if (-not $KeepLayout) {
        & $remove -RepoRoot $RepoRoot
    }
}
