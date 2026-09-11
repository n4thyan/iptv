[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Path,

    [string]$PlaylistUrl = "https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u",
    [string]$EpgUrl = "https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz",
    [switch]$NoBackup
)

$ErrorActionPreference = "Stop"

$resolved = (Resolve-Path -LiteralPath $Path).Path
$raw = Get-Content -LiteralPath $resolved -Raw -Encoding UTF8
[xml]$xml = $raw

if ($null -eq $xml.settings) {
    throw "The file does not contain a Kodi <settings> root element: $resolved"
}

if (-not $NoBackup) {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backup = "$resolved.backup-$timestamp"
    Copy-Item -LiteralPath $resolved -Destination $backup -Force
    Write-Host "Backup: $backup"
}

function Set-KodiSetting {
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][string]$Value
    )

    $node = @($xml.settings.setting | Where-Object { $_.id -eq $Id }) | Select-Object -First 1
    if ($null -eq $node) {
        $node = $xml.CreateElement("setting")
        $node.SetAttribute("id", $Id)
        [void]$xml.settings.AppendChild($node)
    }
    $node.InnerText = $Value
}

# IPTV Simple uses 1 for REMOTE_PATH.  Keep both M3U and XMLTV on GitHub so the
# Xbox does not depend on this PC after the one-time setup/transfer.
Set-KodiSetting -Id "m3uPathType" -Value "1"
Set-KodiSetting -Id "m3uUrl" -Value $PlaylistUrl
Set-KodiSetting -Id "m3uCache" -Value "true"
Set-KodiSetting -Id "epgPathType" -Value "1"
Set-KodiSetting -Id "epgUrl" -Value $EpgUrl
Set-KodiSetting -Id "epgCache" -Value "true"

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$writerSettings = New-Object System.Xml.XmlWriterSettings
$writerSettings.Encoding = $utf8NoBom
$writerSettings.Indent = $true
$writerSettings.NewLineChars = "`n"
$writerSettings.NewLineHandling = [System.Xml.NewLineHandling]::Replace
$writer = [System.Xml.XmlWriter]::Create($resolved, $writerSettings)
try {
    $xml.Save($writer)
}
finally {
    $writer.Dispose()
}

Write-Host "Patched IPTV Simple settings: $resolved"
Write-Host "M3U : $PlaylistUrl"
Write-Host "EPG : $EpgUrl"
Write-Host "Copy this file back to special://profile/addon_data/pvr.iptvsimple/ and restart Kodi."
