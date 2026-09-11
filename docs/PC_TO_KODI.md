# PC → Xbox Kodi setup/maintenance

The PC is a **setup and maintenance tool**, not a server that must stay on.

Normal Xbox playback uses the generated GitHub endpoints:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- EPG: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

The PC can therefore be switched off after setup.

## Fastest method: type into Kodi from the PC

For the M3U and EPG URLs, the safest/easiest route is Kodi's supported JSON-RPC remote-input API. This avoids typing the long URLs with the Xbox controller **and** avoids editing Kodi's internal settings XML.

### One-time Kodi setting

On Xbox Kodi enable:

**Settings → Services → Control → Allow remote control via HTTP**

Note the port (normally `8080`) and any username/password you configure. The Xbox and PC must be on the same home LAN.

### Send one of our URLs

1. On the Xbox, open the M3U or XMLTV URL field so Kodi's on-screen keyboard is visible.
2. On the PC, from this repository, double-click:

   `tools\kodi-url-helper.cmd`

3. Enter the Xbox/Kodi IP address when asked.
4. Choose:
   - `1` = full English generated M3U (recommended),
   - `2` = generated XMLTV EPG,
   - `3` = UK-only generated M3U,
   - `4` = custom text.
5. The PC sends the full text to Kodi with JSON-RPC `Input.SendText`.
6. Check the value on the TV and press **OK** on Kodi's keyboard.

The underlying PowerShell helper is `tools/kodi-send-text.ps1`, so it can also be scripted directly. Example:

```powershell
.\tools\kodi-send-text.ps1 `
  -KodiIp 192.168.0.50 `
  -Text "https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u"
```

If Kodi's HTTP control has authentication enabled, supply `-Username` and `-Password` to the PowerShell helper. Do not expose Kodi's HTTP control port to the public internet; it only needs to be reachable on the home LAN.

For initial IPTV setup this JSON-RPC method is preferred over directly replacing add-on settings files.

## SMB transfer method for files/backups

The PC-to-Kodi SMB workflow remains useful for actual files: keymaps, skin config, logos, backups, and an exported IPTV Simple settings file if we specifically need to inspect it.

### Start the temporary share

From the repository on Windows, double-click:

`tools\start-kodi-transfer.cmd`

Accept the UAC prompt. Or run elevated PowerShell:

```powershell
.\tools\prepare-kodi-transfer.ps1 -CreateShare
```

The helper:

- creates `output\kodi-transfer\`;
- downloads the current generated playlist, guide and diagnostics for inspection;
- verifies the downloaded M3Us/guide are real non-empty files;
- creates `from-xbox\` and `to-xbox\` folders;
- prints the likely LAN IPv4 and SMB path;
- writes `README-XBOX.txt` with the detected PC details;
- creates a temporary SMB share named `KodiTransfer` using the current Windows account.

Kodi may ask for Windows credentials. Use the actual Windows/Microsoft-account password rather than a Windows Hello PIN.

The helper does **not** enable guest SMB, create an anonymous write share, or disable the Windows firewall. If the trusted home LAN is marked **Public**, Windows may block SMB; change that trusted network to **Private** rather than disabling the firewall globally.

### Browse it from Kodi

On Xbox Kodi:

1. Open **Settings → File manager**.
2. Browse/add `smb://PC-NAME/KodiTransfer`.
3. If hostname discovery fails, use the IP form printed by the helper, e.g. `smb://192.168.x.x/KodiTransfer`.
4. Kodi's **Profile directory** contains its user data, including `addon_data/pvr.iptvsimple/`.

## Advanced fallback: patch an exported IPTV Simple instance file

Only use this if remote text entry is inconvenient or we specifically want to inspect/backup the add-on settings.

1. Copy the active `instance-settings-*.xml` from `Profile directory/addon_data/pvr.iptvsimple/` to `KodiTransfer/from-xbox/`.
2. On the PC run:

```powershell
.\tools\patch-iptvsimple-settings.ps1 .\output\kodi-transfer\from-xbox\instance-settings-N.xml
```

The patcher makes a timestamped backup, preserves unrelated settings, and sets the generated English M3U and XMLTV URLs with caching enabled.

If using this advanced method, patch only the active IPTV Simple instance. Do not blindly replace every `instance-settings-*.xml` file left by earlier test configurations.

## Stop the temporary SMB share

Double-click:

`tools\stop-kodi-transfer.cmd`

or run elevated PowerShell:

```powershell
.\tools\prepare-kodi-transfer.ps1 -RemoveShare
```

The local transfer folder remains on the PC unless you delete it manually.

## Recommended division of labour

- **Long URL entry:** PC → Kodi JSON-RPC helper.
- **Files/backups/keymaps/artwork:** temporary SMB share.
- **Normal live TV + EPG:** Kodi reads GitHub directly; PC off.
- **Stream-health audit:** optional PC maintenance with `tools/validate_streams.py`.

This keeps the Xbox setup convenient without turning the PC into a permanent IPTV server.
