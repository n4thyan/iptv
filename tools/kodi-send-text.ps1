[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$KodiIp,
    [Parameter(Mandatory = $true)][string]$Text,
    [int]$Port = 8080,
    [string]$Username = "",
    [string]$Password = "",
    [switch]$Done
)

$ErrorActionPreference = "Stop"

function Invoke-KodiJsonRpc {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [hashtable]$Params = @{}
    )

    $uri = "http://${KodiIp}:${Port}/jsonrpc"
    $body = @{
        jsonrpc = "2.0"
        method = $Method
        params = $Params
        id = 1
    } | ConvertTo-Json -Depth 6 -Compress

    $invoke = @{
        Uri = $uri
        Method = "Post"
        ContentType = "application/json"
        Body = $body
        TimeoutSec = 8
    }

    if ($Username) {
        $raw = "${Username}:${Password}"
        $token = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($raw))
        $invoke.Headers = @{ Authorization = "Basic $token" }
    }

    return Invoke-RestMethod @invoke
}

try {
    $ping = Invoke-KodiJsonRpc -Method "JSONRPC.Ping"
    if ($ping.result -ne "pong") {
        throw "Kodi JSON-RPC did not return pong."
    }
}
catch {
    throw @"
Could not reach Kodi JSON-RPC at http://${KodiIp}:${Port}/jsonrpc.
On Kodi enable Settings > Services > Control > Allow remote control via HTTP,
confirm the port/username/password, and make sure the PC and Xbox are on the same LAN.
Underlying error: $($_.Exception.Message)
"@
}

$params = @{
    text = $Text
    done = [bool]$Done
}
$response = Invoke-KodiJsonRpc -Method "Input.SendText" -Params $params
if ($response.error) {
    throw "Kodi returned JSON-RPC error: $($response.error | ConvertTo-Json -Compress)"
}

Write-Host "Sent $($Text.Length) characters to Kodi."
if (-not $Done) {
    Write-Host "The Kodi on-screen keyboard remains open; confirm it on the Xbox when ready."
}
