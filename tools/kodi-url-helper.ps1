[CmdletBinding()]
param(
    [string]$KodiIp = "",
    [int]$Port = 8080,
    [string]$Username = "",
    [string]$Password = ""
)

$ErrorActionPreference = "Stop"
$statePath = Join-Path $PSScriptRoot ".kodi-helper.local.json"

if (-not $Username) {
    $enteredUsername = Read-Host "Kodi HTTP username [kodi]"
    $Username = if ($enteredUsername) { $enteredUsername } else { "kodi" }
}
if (-not $Password) {
    $Password = Read-Host "Kodi HTTP password"
}

function Invoke-KodiPing {
    param([Parameter(Mandatory = $true)][string]$Ip)

    $uri = "http://${Ip}:${Port}/jsonrpc"
    $body = '{"jsonrpc":"2.0","method":"JSONRPC.Ping","id":1}'
    $raw = "${Username}:${Password}"
    $token = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($raw))

    try {
        $response = Invoke-RestMethod -Uri $uri -Method Post -Headers @{ Authorization = "Basic $token" } -ContentType "application/json" -Body $body -TimeoutSec 2
        return ($response.result -eq "pong")
    }
    catch {
        return $false
    }
}

if (-not $KodiIp -and (Test-Path $statePath)) {
    try {
        $saved = Get-Content -Raw $statePath | ConvertFrom-Json
        if ($saved.ip -and (Invoke-KodiPing -Ip ([string]$saved.ip))) {
            $KodiIp = [string]$saved.ip
            Write-Host "Using saved Xbox/Kodi IP: $KodiIp"
        }
    }
    catch {
        # Ignore stale/corrupt local state and discover again.
    }
}

if (-not $KodiIp) {
    Write-Host "Looking for Kodi on devices already visible on the LAN..."
    $candidates = @()
    foreach ($line in (arp -a)) {
        if ($line -match '^\s*(\d+\.\d+\.\d+\.\d+)\s+[0-9a-fA-F-]{17}\s+dynamic\s*$') {
            $ip = $Matches[1]
            if ($ip -notlike '169.254.*' -and $ip -notlike '*.255') {
                $candidates += $ip
            }
        }
    }

    $matches = @()
    foreach ($candidate in ($candidates | Sort-Object -Unique)) {
        if (Invoke-KodiPing -Ip $candidate) {
            $matches += $candidate
        }
    }

    if ($matches.Count -eq 1) {
        $KodiIp = $matches[0]
        Write-Host "Found Kodi automatically at $KodiIp"
    }
    elseif ($matches.Count -gt 1) {
        Write-Host "Multiple Kodi instances answered: $($matches -join ', ')"
        $KodiIp = Read-Host "Xbox/Kodi IP address"
    }
    else {
        $KodiIp = Read-Host "Could not auto-detect Kodi. Xbox/Kodi IP address"
    }
}

if (-not $KodiIp) {
    throw "Kodi IP address is required."
}
if (-not (Invoke-KodiPing -Ip $KodiIp)) {
    throw "Kodi did not accept JSON-RPC at http://${KodiIp}:${Port}/jsonrpc. Check the HTTP username/password and that remote control via HTTP is enabled."
}

@{ ip = $KodiIp; port = $Port } | ConvertTo-Json | Set-Content -Encoding UTF8 $statePath

Write-Host ""
Write-Host "Choose what to type into the CURRENT Kodi text box:"
Write-Host "  1  Curated English M3U (recommended)"
Write-Host "  2  Xbox-optimised XMLTV EPG (recommended)"
Write-Host "  3  Curated UK-only M3U"
Write-Host "  4  Full English M3U"
Write-Host "  5  Full UK-only M3U"
Write-Host "  6  Full XMLTV EPG (heavier)"
Write-Host "  7  Custom text"
$choice = Read-Host "Choice"

switch ($choice) {
    "1" { $text = "https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u" }
    "2" { $text = "https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz" }
    "3" { $text = "https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-uk.m3u" }
    "4" { $text = "https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u" }
    "5" { $text = "https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u" }
    "6" { $text = "https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-full.xml.gz" }
    "7" { $text = Read-Host "Text to send" }
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
