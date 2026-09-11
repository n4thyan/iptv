param(
    [string]$Source = "https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u",
    [int]$Workers = 24,
    [double]$Timeout = 8,
    [int]$Attempts = 2,
    [int]$DropAfter = 3
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found on PATH."
}

if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    throw "ffprobe was not found on PATH. Install FFmpeg first, then re-run this script."
}

Write-Host "Validating IPTV streams from this PC/network..."
Write-Host "Source: $Source"
Write-Host "Workers: $Workers  Timeout: ${Timeout}s  Attempts: $Attempts  Drop-after: $DropAfter runs"
Write-Host ""

python tools/validate_streams.py $Source `
    --workers $Workers `
    --timeout $Timeout `
    --attempts $Attempts `
    --drop-after $DropAfter

if ($LASTEXITCODE -ne 0) {
    throw "Stream validation failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "Done. Review:"
Write-Host "  output/stream-health-summary.json"
Write-Host "  output/stream-health.json"
Write-Host "  output/english-validated.m3u"
Write-Host ""
Write-Host "The script keeps geo/access-restricted streams and does not remove ordinary failures after only one run."
