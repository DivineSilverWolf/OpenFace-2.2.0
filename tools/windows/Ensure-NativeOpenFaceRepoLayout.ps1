#requires -Version 5.1
<#
.SYNOPSIS
  Creates directory junctions at the repo root so native OpenFace exes find the same
  relative paths as in the Docker image (model/, classifiers/, AU_predictors/).

.DESCRIPTION
  Safe to run on CI: only creates links if missing; if a name exists as a real directory
  or a link pointing elsewhere, the script fails with a clear message (no overwrites).

.PARAMETER RepoRoot
  OpenFace repository root (folder containing vcpkg.json). Default: two levels above this script.
#>
param(
    [Parameter(Mandatory = $false)]
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$junctions = @(
    @{ Name = "model"; Target = Join-Path $RepoRoot "lib\local\LandmarkDetector\model" }
    @{ Name = "classifiers"; Target = Join-Path $RepoRoot "lib\3rdParty\OpenCV\classifiers" }
    @{ Name = "AU_predictors"; Target = Join-Path $RepoRoot "lib\local\FaceAnalyser\AU_predictors" }
)

foreach ($j in $junctions) {
    $link = Join-Path $RepoRoot $j.Name
    $target = $j.Target
    if (-not (Test-Path -LiteralPath $target)) {
        throw "Missing expected target directory: $target"
    }
    if (-not (Test-Path -LiteralPath $link)) {
        New-Item -ItemType Junction -Path $link -Target $target | Out-Null
        Write-Host "Created junction: $link -> $target"
        continue
    }
    $item = Get-Item -LiteralPath $link -Force
    if ($item.LinkType -ne "Junction" -and $item.LinkType -ne "SymbolicLink") {
        throw "Refusing to touch '$link': exists as a normal directory/file, not a junction. Remove or rename it manually."
    }
    Write-Host "OK (existing reparse point): $link"
}
