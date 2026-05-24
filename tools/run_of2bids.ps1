# Run of2bids with PYTHONPATH set to repo tools/ (Windows).
# Usage (from anywhere):  pwsh -File tools/run_of2bids.ps1 --bids-root D:\bids --subject 01 --task rest ...
# Or from repo root:        .\tools\run_of2bids.ps1 --bids-root ... 
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = (Join-Path $RepoRoot "tools")
Set-Location $RepoRoot
python -m of2bids @args
exit $LASTEXITCODE
