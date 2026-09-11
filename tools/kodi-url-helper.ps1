[CmdletBinding()]
param(
    [string]$KodiIp = "",
    [int]$Port = 8080,
    [string]$Username = "",
    [string]$Password = ""
)

$ErrorActionPreference = "Stop"

if (-not $KodiIp) {
    $KodiIp = Read-Host "Xbox/Kodi IP address"
}
if (-not $KodiIp) {
    throw "Kodi IP address is required."
}

Write-Host ""
Write-Host "Choose what to type into the CURRENT Kodi text box:"
Write-Host "  1  Full English generated M3U (recommended)"
Write-Host "  2  Generated XMLTV EPG"
Write-Host "  3  UK-only generated M3U"
Write-Host "  4  Custom text"
$choice = Read-Host "Choice"

switch ($choice) {
    "1" { $text = "https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u" }
    "2" { $text = "https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz" }
    "3" { $text = "https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u" }
    "4" { $text = Read-Host "Text to send" }
    default { throw "Unknown choice: $choice" }
}

if (-not $text) {
    throw "Nothing to send."
}

Write-Host ""
Write-Host "On the Xbox, open the target field so Kodi's on-screen keyboard is visible."
Read-Host "Press Enter here when the Kodi keyboard is open" | Out-Null

$helper = Join-Path $PSScriptRoot "kodi-send-text.ps1"
& $helper -KodiIp $KodiIp -Port $Port -Username $Username -Password $Password -Text $text

Write-Host ""
Write-Host "Text sent. Check the Kodi field, then press OK on the Xbox keyboard."
