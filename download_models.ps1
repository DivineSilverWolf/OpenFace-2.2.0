#requires -Version 5.1
<#
.SYNOPSIS
    Download CEN patch expert models (Dropbox / OneDrive / optional mirror).

.DESCRIPTION
    Same destinations as before. Optional -MirrorBaseUrl or env OPENFACE_MIRROR_BASE_URL
    points to a folder of release assets (e.g. GitHub Releases) where files are named
    cen_patches_0.25_of.dat, etc.

.PARAMETER MirrorBaseUrl
    Base URL ending with optional slash; leaf files are appended. Example:
    https://github.com/ORG/OpenFace-2.2.0/releases/download/openface-assets-v1/

.PARAMETER MaxRetriesPerUri
    Retries per URL before trying the next source (default 5).

.PARAMETER TimeoutSec
    Invoke-WebRequest timeout per attempt (default 120).
#>
param(
    [string]$MirrorBaseUrl,
    [int]$MaxRetriesPerUri = 5,
    [int]$TimeoutSec = 120
)

$ErrorActionPreference = 'Stop'
$ScriptDir = $PSScriptRoot
. (Join-Path $ScriptDir 'tools/asset-download/OpenFaceAssetDownload.ps1')

if (-not $PSBoundParameters.ContainsKey('MirrorBaseUrl') -or [string]::IsNullOrWhiteSpace($MirrorBaseUrl)) {
    $MirrorBaseUrl = $env:OPENFACE_MIRROR_BASE_URL
}

# Determine correct path to the model files (unchanged behaviour)
if ([System.IO.Directory]::Exists((Join-Path (Get-Location) 'lib'))) {
    $modelPath = "lib/local/LandmarkDetector/"
}
else {
    $modelPath = ""
}

$assets = @(
    @{
        Rel        = "model/patch_experts/cen_patches_0.25_of.dat"
        MirrorLeaf = "cen_patches_0.25_of.dat"
        Dropbox    = "https://www.dropbox.com/s/7na5qsjzz8yfoer/cen_patches_0.25_of.dat?dl=1"
        OneDrive   = "https://onedrive.live.com/download?cid=2E2ADA578BFF6E6E&resid=2E2ADA578BFF6E6E%2153072&authkey=AKqoZtcN0PSIZH4"
    },
    @{
        Rel        = "model/patch_experts/cen_patches_0.35_of.dat"
        MirrorLeaf = "cen_patches_0.35_of.dat"
        Dropbox    = "https://www.dropbox.com/s/k7bj804cyiu474t/cen_patches_0.35_of.dat?dl=1"
        OneDrive   = "https://onedrive.live.com/download?cid=2E2ADA578BFF6E6E&resid=2E2ADA578BFF6E6E%2153079&authkey=ANpDR1n3ckL_0gs"
    },
    @{
        Rel        = "model/patch_experts/cen_patches_0.50_of.dat"
        MirrorLeaf = "cen_patches_0.50_of.dat"
        Dropbox    = "https://www.dropbox.com/s/ixt4vkbmxgab1iu/cen_patches_0.50_of.dat?dl=1"
        OneDrive   = "https://onedrive.live.com/download?cid=2E2ADA578BFF6E6E&resid=2E2ADA578BFF6E6E%2153074&authkey=AGi-e30AfRc_zvs"
    },
    @{
        Rel        = "model/patch_experts/cen_patches_1.00_of.dat"
        MirrorLeaf = "cen_patches_1.00_of.dat"
        Dropbox    = "https://www.dropbox.com/s/2t5t1sdpshzfhpj/cen_patches_1.00_of.dat?dl=1"
        OneDrive   = "https://onedrive.live.com/download?cid=2E2ADA578BFF6E6E&resid=2E2ADA578BFF6E6E%2153070&authkey=AD6KjtYipphwBPc"
    }
)

$i = 0
foreach ($a in $assets) {
    $i++
    $rel = $modelPath + $a.Rel
    $destination = Join-Path (Get-Location) $rel
    $dir = Split-Path -Parent $destination
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    if ([System.IO.File]::Exists($destination)) {
        Write-Host "[skip $($i)/$($assets.Count)] already exists: $rel" -ForegroundColor DarkGray
        continue
    }

    Write-Host "=== Model $($i)/$($assets.Count): $rel ===" -ForegroundColor Yellow
    $uris = @()
    if (-not [string]::IsNullOrWhiteSpace($MirrorBaseUrl)) {
        $uris += (Join-OpenFaceMirrorUrl -BaseUrl $MirrorBaseUrl -LeafName $a.MirrorLeaf)
    }
    $uris += $a.Dropbox
    $uris += $a.OneDrive

    Save-OpenFaceAsset -Destination $destination -CandidateUris $uris -Label $rel `
        -MaxRetriesPerUri $MaxRetriesPerUri -TimeoutSec $TimeoutSec
}

Write-Host "download_models.ps1 finished." -ForegroundColor Green
