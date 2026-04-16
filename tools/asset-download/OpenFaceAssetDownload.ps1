# Shared helpers for download_models.ps1 and download_libraries.ps1 (dot-source from repo root).
# Requires Windows PowerShell 5.1+ or PowerShell 7+.

function Join-OpenFaceMirrorUrl {
    <#
    .SYNOPSIS
    Join a mirror base URL (e.g. GitHub release asset folder) with a leaf filename.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [Parameter(Mandatory = $true)][string]$LeafName
    )
    $b = $BaseUrl.TrimEnd('/')
    $leaf = $LeafName.TrimStart('/')
    return "$b/$leaf"
}

function Invoke-OpenFaceWebDownload {
    <#
    .SYNOPSIS
    Invoke-WebRequest with retries, timeout, and basic progress logging.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$OutFile,
        [int]$MaxRetries = 5,
        [int]$TimeoutSec = 120,
        [string]$LogLabel = ''
    )
    $parent = Split-Path -Parent -Path $OutFile
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    $attempt = 0
    while ($attempt -lt $MaxRetries) {
        $attempt++
        $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
        try {
            Write-Host "[$stamp] [try $attempt/$MaxRetries] GET $LogLabel" -ForegroundColor Cyan
            Write-Host "           $Uri"
            Invoke-WebRequest -Uri $Uri -OutFile $OutFile -UseBasicParsing -TimeoutSec $TimeoutSec
            if ((Test-Path -LiteralPath $OutFile) -and ((Get-Item -LiteralPath $OutFile).Length -gt 0)) {
                $bytes = (Get-Item -LiteralPath $OutFile).Length
                Write-Host "[$stamp] [ok] $LogLabel -> $OutFile ($bytes bytes)" -ForegroundColor Green
                return
            }
            throw "Downloaded file missing or empty: $OutFile"
        }
        catch {
            $msg = $_.Exception.Message
            Write-Warning "[$stamp] [fail try $attempt/$MaxRetries] $LogLabel : $msg"
            if ($attempt -ge $MaxRetries) {
                throw
            }
            $delay = [Math]::Min(30, 2 * $attempt)
            Write-Host "           sleeping ${delay}s before retry..." -ForegroundColor DarkYellow
            Start-Sleep -Seconds $delay
        }
    }
}

function Save-OpenFaceAsset {
    <#
    .SYNOPSIS
    Try each candidate URI in order (mirror, Dropbox, OneDrive, ...). First success wins.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Destination,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string[]]$CandidateUris,
        [string]$Label = '',
        [int]$MaxRetriesPerUri = 5,
        [int]$TimeoutSec = 120
    )
    $destFull = [System.IO.Path]::GetFullPath($Destination)
    foreach ($uri in $CandidateUris) {
        if ([string]::IsNullOrWhiteSpace($uri)) { continue }
        try {
            Invoke-OpenFaceWebDownload -Uri $uri -OutFile $destFull -MaxRetries $MaxRetriesPerUri `
                -TimeoutSec $TimeoutSec -LogLabel $(if ($Label) { $Label } else { $destFull })
            return
        }
        catch {
            Write-Warning "Source failed, trying next if any: $uri"
        }
    }
    throw "All download sources failed for: $Label ($destFull)"
}
