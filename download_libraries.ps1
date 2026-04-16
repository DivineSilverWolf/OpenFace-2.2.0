#requires -Version 5.1
<#
.SYNOPSIS
    Download OpenCV prebuilt DLLs (Dropbox / OneDrive / optional mirror).

.DESCRIPTION
    Same layout and URLs as the legacy script, with retries, timeouts, logging,
    and optional mirror first. Uncommented Dropbox URLs for opencv_world* match
    historical script comments (restored as middle fallback before OneDrive).

.PARAMETER MirrorBaseUrl
    Same as download_models.ps1; see docs/ASSET_DOWNLOAD.md for required mirror leaf file names.

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

$assets = @(
    @{
        Rel        = "lib/3rdParty/OpenCV/bin/opencv_ffmpeg410_64.dll"
        MirrorLeaf = "opencv_ffmpeg410_64.dll"
        Dropbox    = "https://www.dropbox.com/s/gvkd4549wsjvn3u/opencv_ffmpeg410_64.dll?dl=1"
        OneDrive   = "https://onedrive.live.com/download?cid=2E2ADA578BFF6E6E&resid=2E2ADA578BFF6E6E%2153244&authkey=AEuLAF197Sy7S3M"
    },
    @{
        Rel        = "lib/3rdParty/OpenCV/x64/v141/bin/Release/opencv_world410.dll"
        MirrorLeaf = "opencv_world410_x64_Release.dll"
        Dropbox    = "https://www.dropbox.com/s/c81shi8br57xytv/opencv_world410.dll?dl=1"
        OneDrive   = "https://onedrive.live.com/download?cid=2E2ADA578BFF6E6E&resid=2E2ADA578BFF6E6E%2153246&authkey=AJkwseAGKqL3PpU"
    },
    @{
        Rel        = "lib/3rdParty/OpenCV/x64/v141/bin/Debug/opencv_world410d.dll"
        MirrorLeaf = "opencv_world410_x64_Debug.dll"
        Dropbox    = "https://www.dropbox.com/s/8a4kmvpj5a09jdz/opencv_world410d.dll?dl=1"
        OneDrive   = "https://onedrive.live.com/download?cid=2E2ADA578BFF6E6E&resid=2E2ADA578BFF6E6E%2153247&authkey=AJE4pLhzjtkPDWs"
    },
    @{
        Rel        = "lib/3rdParty/OpenCV/bin/opencv_ffmpeg410.dll"
        MirrorLeaf = "opencv_ffmpeg410.dll"
        Dropbox    = "https://www.dropbox.com/s/7pada6etpui97f7/opencv_ffmpeg410.dll?dl=1"
        OneDrive   = "https://onedrive.live.com/download?cid=2E2ADA578BFF6E6E&resid=2E2ADA578BFF6E6E%2153252&authkey=AEwNPWYZ7sOOhXo"
    },
    @{
        Rel        = "lib/3rdParty/OpenCV/x86/v141/bin/Release/opencv_world410.dll"
        MirrorLeaf = "opencv_world410_x86_Release.dll"
        Dropbox    = "https://www.dropbox.com/s/qf4rqphvrj2k4d1/opencv_world410.dll?dl=1"
        OneDrive   = "https://onedrive.live.com/download?cid=2E2ADA578BFF6E6E&resid=2E2ADA578BFF6E6E%2153255&authkey=AJ0S3GY4fCYKFXo"
    },
    @{
        Rel        = "lib/3rdParty/OpenCV/x86/v141/bin/Debug/opencv_world410d.dll"
        MirrorLeaf = "opencv_world410_x86_Debug.dll"
        Dropbox    = "https://www.dropbox.com/s/kafps88dbdlg5y2/opencv_world410d.dll?dl=1"
        OneDrive   = "https://onedrive.live.com/download?cid=2E2ADA578BFF6E6E&resid=2E2ADA578BFF6E6E%2153256&authkey=ALbDTeRByHmWO-M"
    }
)

$i = 0
foreach ($a in $assets) {
    $i++
    $destination = Join-Path (Get-Location) $a.Rel
    $dir = Split-Path -Parent $destination
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    if ([System.IO.File]::Exists($destination)) {
        Write-Host "[skip $($i)/$($assets.Count)] already exists: $($a.Rel)" -ForegroundColor DarkGray
        continue
    }

    Write-Host "=== Library $($i)/$($assets.Count): $($a.Rel) ===" -ForegroundColor Yellow
    $uris = @()
    if (-not [string]::IsNullOrWhiteSpace($MirrorBaseUrl)) {
        $uris += (Join-OpenFaceMirrorUrl -BaseUrl $MirrorBaseUrl -LeafName $a.MirrorLeaf)
    }
    $uris += $a.Dropbox
    $uris += $a.OneDrive

    Save-OpenFaceAsset -Destination $destination -CandidateUris $uris -Label $a.Rel `
        -MaxRetriesPerUri $MaxRetriesPerUri -TimeoutSec $TimeoutSec
}

Write-Host "download_libraries.ps1 finished." -ForegroundColor Green
