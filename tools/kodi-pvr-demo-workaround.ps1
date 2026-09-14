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
    $Username = if ($enteredUsername) { $enteredUsername.Trim() } else { "kodi" }
}
if (-not $Password) {
    $Password = Read-Host "Kodi HTTP password"
}

if (-not $KodiIp -and (Test-Path $statePath)) {
    try {
        $saved = Get-Content -Raw $statePath | ConvertFrom-Json
        if ($saved.ip) { $KodiIp = ([string]$saved.ip).Trim() }
        if ($saved.port) { $Port = [int]$saved.port }
    }
    catch {}
}
if (-not $KodiIp) {
    $KodiIp = (Read-Host "Xbox/Kodi IP address").Trim()
}
else {
    $KodiIp = $KodiIp.Trim()
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

function Get-Addon([string]$AddonId) {
    return Invoke-KodiJsonRpc -Method "Addons.GetAddonDetails" -Params @{
        addonid = $AddonId
        properties = @("name", "version", "enabled")
    }
}

function Set-AddonEnabled([string]$AddonId, [bool]$Enabled) {
    Invoke-KodiJsonRpc -Method "Addons.SetAddonEnabled" -Params @{
        addonid = $AddonId
        enabled = $Enabled
    } | Out-Null
}

function Test-PvrAvailable {
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

Write-Host "Kodi Xbox PVR 0% workaround"
Write-Host "============================"
Write-Host "Target: $KodiIp`:$Port"

$ping = Invoke-KodiJsonRpc -Method "JSONRPC.Ping"
if ($ping -ne "pong") { throw "Kodi did not return pong." }
Write-Host "JSON-RPC: OK"

$demo = Get-Addon "pvr.demo"
$iptv = Get-Addon "pvr.iptvsimple"
Write-Host ("Demo PVR Client: v{0}, enabled={1}" -f $demo.addon.version, $demo.addon.enabled)
Write-Host ("IPTV Simple Client: v{0}, enabled={1}" -f $iptv.addon.version, $iptv.addon.enabled)

Write-Host ""
Write-Host "Applying upstream Kodi 21 PVR startup workaround..."
Write-Host "1. Temporarily disable IPTV Simple"
Set-AddonEnabled "pvr.iptvsimple" $false
Start-Sleep -Seconds 2

Write-Host "2. Enable Demo PVR Client"
Set-AddonEnabled "pvr.demo" $true
Start-Sleep -Seconds 5

Write-Host "3. Re-enable IPTV Simple"
Set-AddonEnabled "pvr.iptvsimple" $true
Start-Sleep -Seconds 8

Write-Host ""
$available = Test-PvrAvailable
if ($available) {
    Write-Host ""
    Write-Host "SUCCESS: Kodi now reports PVR as available."
    Write-Host "Leave Demo PVR Client installed/enabled for the moment and open TV on the Xbox."
    Write-Host "Once IPTV Simple channels are visible, Demo PVR can be disabled if desired."
    Write-Host "Do not remove Demo PVR on Xbox; upstream reports the 0% issue can return after removal."
}
else {
    Write-Host ""
    Write-Host "PVR still is not available after the Demo PVR workaround."
    Write-Host "Next step: enable Kodi debug logging and capture/upload kodi.log so the exact PVR startup failure can be inspected."
    exit 2
}
