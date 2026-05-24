#requires -Version 5.1
# AST-parse download scripts (no network). Run from repo root:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tests/download_assets_parse.tests.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Test-ParseOk([string]$relativePath) {
    $full = Join-Path $root $relativePath
    if (-not (Test-Path -LiteralPath $full)) {
        Write-Error "Missing: $full"
        exit 1
    }
    $tokens = $null
    $errors = $null
    $ast = [System.Management.Automation.Language.Parser]::ParseFile($full, [ref]$tokens, [ref]$errors)
    if ($errors -and $errors.Count -gt 0) {
        foreach ($e in $errors) {
            Write-Host "Parse error in ${relativePath}: $($e.Message)" -ForegroundColor Red
        }
        exit 1
    }
    Write-Host "Parse OK: $relativePath" -ForegroundColor Green
}

Test-ParseOk 'tools/asset-download/OpenFaceAssetDownload.ps1'
Test-ParseOk 'download_models.ps1'
Test-ParseOk 'download_libraries.ps1'

Write-Host 'download_assets_parse.tests.ps1: all checks passed.' -ForegroundColor Green
exit 0
