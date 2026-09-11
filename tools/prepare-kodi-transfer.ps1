[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "..\output\kodi-transfer"),
    [string]$ShareName = "KodiTransfer",
    [switch]$CreateShare,
    [switch]$RemoveShare
)

$ErrorActionPreference = "Stop"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if ($RemoveShare) {
    $existing = Get-SmbShare -Name $ShareName -ErrorAction SilentlyContinue
    if ($null -ne $existing) {
        if (-not (Test-IsAdministrator)) {
            throw "Run PowerShell as Administrator to remove SMB share '$ShareName'."
        }
        Remove-SmbShare -Name $ShareName -Force
        Write-Host "Removed SMB share: $ShareName"
    }
    else {
        Write-Host "SMB share '$ShareName' does not exist."
    }
    return
}

$root = [IO.Path]::GetFullPath($OutputDirectory)
$fromXbox = Join-Path $root "from-xbox"
$toXbox = Join-Path $root "to-xbox"
New-Item -ItemType Directory -Force -Path $root, $fromXbox, $toXbox | Out-Null

$downloads = @{
    "english.m3u" = "https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u"
    "uk.m3u" = "https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u"
    "guide.xml.gz" = "https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz"
    "last-update.txt" = "https://raw.githubusercontent.com/n4thyan/iptv/generated/last-update.txt"
    "guide-stats.json" = "https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-stats.json"
}

foreach ($item in $downloads.GetEnumerator()) {
    $destination = Join-Path $toXbox $item.Key
    try {
        Invoke-WebRequest -Uri $item.Value -OutFile $destination -UseBasicParsing
        if ((Get-Item $destination).Length -eq 0) {
            throw "downloaded file was empty"
        }
        Write-Host "Downloaded $($item.Key)"
    }
    catch {
        Write-Warning "Could not download $($item.Key): $($_.Exception.Message)"
    }
}

$addresses = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
        $_.IPAddress -ne "127.0.0.1" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.InterfaceAlias -notmatch "Loopback"
    } |
    Sort-Object -Property InterfaceMetric, SkipAsSource |
    Select-Object -ExpandProperty IPAddress -Unique)
$bestIp = if ($addresses.Count -gt 0) { $addresses[0] } else { "<PC-IP>" }
$computer = $env:COMPUTERNAME

$instructions = @"
KODI / XBOX TRANSFER PACK
========================

PC hostname: $computer
Likely LAN IPv4: $bestIp
SMB share name: $ShareName

Recommended use
---------------
1. In Kodi open Settings > File manager.
2. Add/browse the Windows SMB share from this PC:
      smb://$computer/$ShareName
   If hostname discovery fails use:
      smb://$bestIp/$ShareName
3. Kodi may ask once for your Windows username/password. Let Kodi remember it.
4. In the other File Manager pane open Profile directory.
5. For normal playlist/EPG use you do NOT need to keep the PC on: IPTV Simple
   should use the GitHub URLs below.

No-long-URL method
------------------
To avoid typing the GitHub URLs on Xbox:

A. In Kodi File Manager browse:
      special://profile/addon_data/pvr.iptvsimple/
B. Copy the active instance-settings-*.xml file into:
      smb://$computer/$ShareName/from-xbox/
C. On the PC run from the repository:
      .\tools\patch-iptvsimple-settings.ps1 `
        .\output\kodi-transfer\from-xbox\instance-settings-N.xml
D. The patcher creates a backup and writes these remote sources into the file:
      M3U: https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u
      EPG: https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz
E. Copy the patched XML back to the same pvr.iptvsimple folder in Kodi, replacing
   the original, then fully quit and reopen Kodi.

IMPORTANT: copy out and patch the instance file that belongs to the configuration
we actually want to keep. Do not blindly replace every instance-settings file.

The files in to-xbox/ are also available if we want to inspect/copy them manually.
The generated M3U/EPG on GitHub refresh independently of this PC.

When finished with the transfer share, remove it with an elevated PowerShell:
      .\tools\prepare-kodi-transfer.ps1 -RemoveShare
"@
$instructionsPath = Join-Path $root "README-XBOX.txt"
$instructions | Set-Content -LiteralPath $instructionsPath -Encoding UTF8

if ($CreateShare) {
    if (-not (Test-IsAdministrator)) {
        throw "Re-run PowerShell as Administrator with -CreateShare to create the SMB share."
    }

    $existing = Get-SmbShare -Name $ShareName -ErrorAction SilentlyContinue
    if ($null -ne $existing) {
        if ([IO.Path]::GetFullPath($existing.Path) -ne $root) {
            throw "SMB share '$ShareName' already exists at '$($existing.Path)'. Remove it first or use another -ShareName."
        }
        Write-Host "SMB share already exists: \\$computer\$ShareName"
    }
    else {
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        New-SmbShare -Name $ShareName -Path $root -ChangeAccess $identity | Out-Null
        Write-Host "Created temporary SMB share: \\$computer\$ShareName"
    }
}

Write-Host ""
Write-Host "Transfer pack: $root"
Write-Host "Xbox SMB path: smb://$computer/$ShareName"
Write-Host "IP fallback   : smb://$bestIp/$ShareName"
Write-Host "Instructions  : $instructionsPath"
if (-not $CreateShare) {
    Write-Host "Run this script as Administrator with -CreateShare when you want the temporary SMB share."
}
