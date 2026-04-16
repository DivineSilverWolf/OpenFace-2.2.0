#requires -Version 5.1
# Unit tests for mirror URL joining (no network). Run from repo root:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tests/asset_download_uri.tests.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
. (Join-Path $root 'tools/asset-download/OpenFaceAssetDownload.ps1')

function Assert-Equal($a, $b, $msg) {
    if ($a -cne $b) {
        Write-Error "FAIL: $msg`n  expected: $b`n  actual:   $a"
        exit 1
    }
}

$u = Join-OpenFaceMirrorUrl -BaseUrl 'https://example.com/a/' -LeafName 'f.dat'
Assert-Equal $u 'https://example.com/a/f.dat' 'trailing slash on base'

$u = Join-OpenFaceMirrorUrl -BaseUrl 'https://example.com/a' -LeafName 'f.dat'
Assert-Equal $u 'https://example.com/a/f.dat' 'no trailing slash on base'

$u = Join-OpenFaceMirrorUrl -BaseUrl 'https://example.com/a//' -LeafName '/g.bin'
Assert-Equal $u 'https://example.com/a/g.bin' 'duplicate slashes trimmed'

Write-Host 'asset_download_uri.tests.ps1: all checks passed.' -ForegroundColor Green
exit 0
