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

function Get-BestLanIPv4 {
    try {
        $configs = @(Get-NetIPConfiguration -ErrorAction Stop |
            Where-Object {
                $null -ne $_.IPv4DefaultGateway -and
                $null -ne $_.IPv4Address -and
                $_.NetAdapter.Status -eq "Up"
            })

        foreach ($config in $configs) {
            foreach ($address in @($config.IPv4Address)) {
                $ip = [string]$address.IPAddress
                if ($ip -match '^192\.168\.' -or
                    $ip -match '^10\.' -or
                    $ip -match '^172\.(1[6-9]|2[0-9]|3[01])\.') {
                    return $ip
                }
            }
        }

        foreach ($config in $configs) {
            foreach ($address in @($config.IPv4Address)) {
                $ip = [string]$address.IPAddress
                if ($ip -and $ip -ne "127.0.0.1" -and $ip -notlike "169.254.*") {
                    return $ip
                }
            }
        }
    }
    catch {
        Write-Verbose "Could not inspect active IP configuration: $($_.Exception.Message)"
    }
    return "<PC-IP>"
}

function Test-DownloadedFile {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "downloaded file does not exist"
    }
    if ((Get-Item -LiteralPath $Path).Length -eq 0) {
        throw "downloaded file was empty"
    }

    switch ($Name) {
        "english.m3u" {
            $first = Get-Content -LiteralPath $Path -TotalCount 1 -Encoding UTF8
            if ($first -notmatch '^#EXTM3U') { throw "playlist did not start with #EXTM3U" }
        }
        "uk.m3u" {
            $first = Get-Content -LiteralPath $Path -TotalCount 1 -Encoding UTF8
            if ($first -notmatch '^#EXTM3U') { throw "playlist did not start with #EXTM3U" }
        }
        "guide.xml.gz" {
            $bytes = [IO.File]::ReadAllBytes($Path)
            if ($bytes.Length -lt 2 -or $bytes[0] -ne 0x1f -or $bytes[1] -ne 0x8b) {
                throw "guide did not have a gzip header"
            }
        }
        "guide-stats.json" {
            $null = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
        }
    }
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

$downloads = [ordered]@{
    "english.m3u" = "https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u"
    "uk.m3u" = "https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u"
    "guide.xml.gz" = "https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz"
    "last-update.txt" = "https://raw.githubusercontent.com/n4thyan/iptv/generated/last-update.txt"
    "guide-stats.json" = "https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-stats.json"
    "epg-coverage.txt" = "https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-coverage.txt"
    "epg-pass-summary.json" = "https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-pass-summary.json"
}

foreach ($item in $downloads.GetEnumerator()) {
    $destination = Join-Path $toXbox $item.Key
    try {
        Invoke-WebRequest -Uri $item.Value -OutFile $destination -UseBasicParsing
        Test-DownloadedFile -Name $item.Key -Path $destination
        Write-Host "Downloaded $($item.Key)"
    }
    catch {
        Remove-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
        Write-Warning "Could not download $($item.Key): $($_.Exception.Message)"
    }
}

$bestIp = Get-BestLanIPv4
$computer = $env:COMPUTERNAME

try {
    $publicProfiles = @(Get-NetConnectionProfile -ErrorAction Stop |
        Where-Object { $_.IPv4Connectivity -ne "Disconnected" -and $_.NetworkCategory -eq "Public" })
    if ($publicProfiles.Count -gt 0) {
        Write-Warning "Your active Windows network is marked Public. SMB is often blocked on Public networks. If Kodi cannot connect, change your trusted home network to Private in Windows Settings rather than disabling the firewall."
    }
}
catch {
    Write-Verbose "Could not inspect Windows network profile: $($_.Exception.Message)"
}

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
3. Kodi may ask once for your Windows username/password. Use the account password,
   not a Windows Hello PIN, and let Kodi remember it for this temporary share.
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

If Kodi cannot reach the share
------------------------------
- Prefer the IP form smb://$bestIp/$ShareName.
- Make sure the PC and Xbox are on the same home network.
- Make sure Windows is using a Private network profile for the trusted home LAN.
- Do not turn the firewall off globally.

When finished with the transfer share, remove it with an elevated PowerShell:
      .\tools\prepare-kodi-transfer.ps1 -RemoveShare
"@
$instructionsPath = Join-Path $root "README-XBOX.txt"
$instructions | Set-Content -LiteralPath $instructionsPath -Encoding UTF8

$urls = @"
M3U=https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u
EPG=https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz
UK_ONLY_M3U=https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u
"@
$urls | Set-Content -LiteralPath (Join-Path $toXbox "SOURCE-URLS.txt") -Encoding UTF8

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
