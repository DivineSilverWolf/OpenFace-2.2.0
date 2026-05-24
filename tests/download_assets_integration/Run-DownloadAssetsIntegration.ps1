#requires -Version 5.1
<#
.SYNOPSIS
    End-to-end download of models + OpenCV DLLs into an isolated workdir/ (gitignored).

.DESCRIPTION
    Creates tests/download_assets_integration/workdir with minimal lib/ layout,
    runs repo-root download_models.ps1 and download_libraries.ps1 from that cwd,
    then verifies file sizes. Requires network.
#>
param(
    [string]$MirrorBaseUrl,
    [int]$MaxRetriesPerUri = 5,
    [int]$TimeoutSec = 120
)

$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $here '..\..')).Path
$workDir = Join-Path $here 'workdir'

Write-Host "=== OpenFace asset download integration ===" -ForegroundColor Cyan
Write-Host "Repo root: $repoRoot"
Write-Host "Work dir:  $workDir"

if (-not [string]::IsNullOrWhiteSpace($MirrorBaseUrl)) {
    Write-Host "Mirror:    $MirrorBaseUrl"
}

Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path (Join-Path $workDir 'lib/local/LandmarkDetector/model/patch_experts') -Force | Out-Null
# download_libraries.ps1 creates OpenCV subdirs itself; lib/ is enough for branch detection

$modelsScript = Join-Path $repoRoot 'download_models.ps1'
$libsScript   = Join-Path $repoRoot 'download_libraries.ps1'
if (-not (Test-Path -LiteralPath $modelsScript)) { throw "Missing: $modelsScript" }
if (-not (Test-Path -LiteralPath $libsScript))   { throw "Missing: $libsScript" }

function Assert-FileOk {
    param(
        [Parameter(Mandatory)][string]$RelativePath,
        [Parameter(Mandatory)][long]$MinBytes
    )
    $full = Join-Path $workDir $RelativePath
    if (-not (Test-Path -LiteralPath $full)) {
        throw "Missing file: $RelativePath ($full)"
    }
    $len = (Get-Item -LiteralPath $full).Length
    if ($len -lt $MinBytes) {
        throw "File too small ($len bytes < $MinBytes): $RelativePath (possible HTML error page)"
    }
    Write-Host "[verify ok] $RelativePath ($len bytes)" -ForegroundColor Green
}

Push-Location $workDir
try {
    $commonArgs = @{
        MaxRetriesPerUri = $MaxRetriesPerUri
        TimeoutSec       = $TimeoutSec
    }
    if (-not [string]::IsNullOrWhiteSpace($MirrorBaseUrl)) {
        $commonArgs['MirrorBaseUrl'] = $MirrorBaseUrl
    }

    Write-Host "`n--- download_models.ps1 ---" -ForegroundColor Yellow
    & $modelsScript @commonArgs

    Write-Host "`n--- download_libraries.ps1 ---" -ForegroundColor Yellow
    & $libsScript @commonArgs

    Write-Host "`n--- verify outputs ---" -ForegroundColor Yellow
    $minModel = 500KB
    Assert-FileOk 'lib/local/LandmarkDetector/model/patch_experts/cen_patches_0.25_of.dat' $minModel
    Assert-FileOk 'lib/local/LandmarkDetector/model/patch_experts/cen_patches_0.35_of.dat' $minModel
    Assert-FileOk 'lib/local/LandmarkDetector/model/patch_experts/cen_patches_0.50_of.dat' $minModel
    Assert-FileOk 'lib/local/LandmarkDetector/model/patch_experts/cen_patches_1.00_of.dat' $minModel

    # OpenCV prebuilt DLLs in this repo are ~100 KB each (not multi-MB); avoid false "HTML stub" failures.
    $minDll = 80KB
    Assert-FileOk 'lib/3rdParty/OpenCV/bin/opencv_ffmpeg410_64.dll' $minDll
    Assert-FileOk 'lib/3rdParty/OpenCV/x64/v141/bin/Release/opencv_world410.dll' $minDll
    Assert-FileOk 'lib/3rdParty/OpenCV/x64/v141/bin/Debug/opencv_world410d.dll' $minDll
    Assert-FileOk 'lib/3rdParty/OpenCV/bin/opencv_ffmpeg410.dll' $minDll
    Assert-FileOk 'lib/3rdParty/OpenCV/x86/v141/bin/Release/opencv_world410.dll' $minDll
    Assert-FileOk 'lib/3rdParty/OpenCV/x86/v141/bin/Debug/opencv_world410d.dll' $minDll
}
finally {
    Pop-Location
}

Write-Host "`n=== Integration PASSED ===" -ForegroundColor Green
exit 0
