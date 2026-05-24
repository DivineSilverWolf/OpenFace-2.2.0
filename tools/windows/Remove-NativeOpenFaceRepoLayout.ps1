#requires -Version 5.1
<#
.SYNOPSIS
  Removes repo-root junctions created by Ensure-NativeOpenFaceRepoLayout.ps1 (only junctions/symlinks).

.PARAMETER RepoRoot
  Repository root. Default: two levels above this script.
#>
param(
    [Parameter(Mandatory = $false)]
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

foreach ($name in @("model", "classifiers", "AU_predictors")) {
    $link = Join-Path $RepoRoot $name
    if (-not (Test-Path -LiteralPath $link)) {
        continue
    }
    $item = Get-Item -LiteralPath $link -Force
    if ($item.LinkType -ne "Junction" -and $item.LinkType -ne "SymbolicLink") {
        Write-Warning "Skip '$link': not a junction/symlink (no changes)."
        continue
    }
    cmd.exe /c "rmdir `"$link`""
    if (Test-Path -LiteralPath $link) {
        throw "Failed to remove junction: $link"
    }
    Write-Host "Removed junction: $link"
}
