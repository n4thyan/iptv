[CmdletBinding()]
param(
    [string]$KodiIp = "",
    [int]$Port = 8080,
    [string]$Username = "",
    [string]$Password = "",
    [switch]$RestartPvrClient
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

if (-not $KodiIp -and (Test-Path $statePath)) {
    try {
        $saved = Get-Content -Raw $statePath | ConvertFrom-Json
        if ($saved.ip) { $KodiIp = [string]$saved.ip }
        if ($saved.port) { $Port = [int]$saved.port }
    }
    catch {}
}
if (-not $KodiIp) {
    $KodiIp = Read-Host "Xbox/Kodi IP address"
}
if (-not $KodiIp) {
    throw "Kodi IP address is required."
}

$raw = "${Username}:${Password}"
$token = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($raw))
$headers = @{ Authorization = "Basic $token" }
$uri = "http://${KodiIp}:${Port}/jsonrpc"

function Invoke-KodiJsonRpc {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [hashtable]$Params = @{}
    )

    $body = @{
        jsonrpc = "2.0"
        method = $Method
        params = $Params
        id = 1
    } | ConvertTo-Json -Depth 8 -Compress

    $response = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -ContentType "application/json" -Body $body -TimeoutSec 8
    if ($response.error) {
        throw "Kodi JSON-RPC error from ${Method}: $($response.error | ConvertTo-Json -Compress)"
    }
    return $response.result
}

Write-Host "Kodi PVR healthcheck"
Write-Host "===================="
Write-Host "Target: $KodiIp`:$Port"

$ping = Invoke-KodiJsonRpc -Method "JSONRPC.Ping"
if ($ping -ne "pong") {
    throw "Kodi did not return pong."
}
Write-Host "JSON-RPC: OK"

try {
    $app = Invoke-KodiJsonRpc -Method "Application.GetProperties" -Params @{ properties = @("name", "version") }
    $v = $app.version
    Write-Host ("Kodi: {0} {1}.{2}.{3} {4}" -f $app.name, $v.major, $v.minor, $v.revision, $v.tag)
}
catch {
    Write-Host "Kodi version query failed: $($_.Exception.Message)"
}

try {
    $addon = Invoke-KodiJsonRpc -Method "Addons.GetAddonDetails" -Params @{
        addonid = "pvr.iptvsimple"
        properties = @("name", "version", "enabled")
    }
    $details = $addon.addon
    Write-Host ("IPTV Simple: {0} v{1}, enabled={2}" -f $details.name, $details.version, $details.enabled)
}
catch {
    Write-Host "IPTV Simple details query failed: $($_.Exception.Message)"
}

function Show-PvrState {
    try {
        $pvr = Invoke-KodiJsonRpc -Method "PVR.GetProperties" -Params @{ properties = @("available", "recording", "scanning") }
        Write-Host ("PVR state: available={0}, scanning={1}, recording={2}" -f $pvr.available, $pvr.scanning, $pvr.recording)
        return [bool]$pvr.available
    }
    catch {
        Write-Host "PVR state query failed: $($_.Exception.Message)"
        return $false
    }
}

$available = Show-PvrState

if ($RestartPvrClient) {
    Write-Host ""
    Write-Host "Restarting IPTV Simple Client without deleting its settings..."
    Invoke-KodiJsonRpc -Method "Addons.SetAddonEnabled" -Params @{ addonid = "pvr.iptvsimple"; enabled = $false } | Out-Null
    Start-Sleep -Seconds 2
    Invoke-KodiJsonRpc -Method "Addons.SetAddonEnabled" -Params @{ addonid = "pvr.iptvsimple"; enabled = $true } | Out-Null
    Start-Sleep -Seconds 5
    $available = Show-PvrState
}

Write-Host ""
if ($available) {
    Write-Host "PVR reports available. If the guide is stale, clear Kodi's PVR/EPG caches once after changing the M3U/XMLTV URLs."
}
else {
    Write-Host "PVR is not available yet. Because the M3U/XMLTV files validate externally, the next recovery step is Kodi's local PVR cache reset."
    Write-Host "Kodi: Settings > PVR & Live TV > General > Clear cache"
    Write-Host "Then: Settings > PVR & Live TV > Guide > Clear cache"
    Write-Host "Finally fully quit Kodi from the Xbox dashboard and reopen it."
}
