# PC → Xbox Kodi setup/maintenance

The PC is a setup and maintenance tool, not a server that must stay on.

Normal Xbox playback uses the generated GitHub endpoints:

- Recommended M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u`
- UK-only curated M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-uk.m3u`
- EPG: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

The broader `english.m3u` and `uk.m3u` outputs are still available for full-list browsing.

## Fastest method: type into Kodi from the PC

For M3U and EPG URLs, the easiest route is Kodi's supported JSON-RPC remote-input API. This avoids typing long URLs with the Xbox controller and avoids editing Kodi's internal settings XML.

### One-time Kodi setting

On Xbox Kodi enable:

**Settings → Services → Control → Allow remote control via HTTP**

Note the port (normally `8080`) and any username/password you configure. Xbox and PC must be on the same home LAN.

### Send one of our URLs

1. On the Xbox, open the M3U or XMLTV URL field so Kodi's on-screen keyboard is visible.
2. On the PC, double-click `tools\kodi-url-helper.cmd`.
3. Enter the Xbox/Kodi IP address.
4. Choose:
   - `1` = curated English M3U (recommended),
   - `2` = generated XMLTV EPG,
   - `3` = curated UK-only M3U,
   - `4` = full English M3U,
   - `5` = full UK M3U,
   - `6` = custom text.
5. Check the value on the TV and press **OK** on Kodi's keyboard.

The underlying helper is `tools/kodi-send-text.ps1` and can be scripted directly. Example:

```powershell
.\tools\kodi-send-text.ps1 `
  -KodiIp 192.168.0.50 `
  -Text "https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u"
```

If Kodi HTTP control has authentication enabled, supply `-Username` and `-Password`. Do not expose Kodi's HTTP control port to the public internet; it only needs to be reachable on the home LAN.

## SMB transfer method for files/backups

The PC-to-Kodi SMB workflow remains useful for actual files: keymaps, skin config, logos, backups and an exported IPTV Simple settings file if we need to inspect it.

### Start the temporary share

From the repository on Windows, double-click `tools\start-kodi-transfer.cmd`, or run elevated PowerShell:

```powershell
.\tools\prepare-kodi-transfer.ps1 -CreateShare
```

The helper:

- creates `output\kodi-transfer\`;
- downloads current curated/full playlists, guide and current diagnostics;
- verifies downloaded playlists/guide are real non-empty files;
- creates `from-xbox\` and `to-xbox\` folders;
- prints the likely LAN IPv4 and SMB path;
- writes `README-XBOX.txt` with the detected PC details;
- creates a temporary SMB share named `KodiTransfer` using the current Windows account.

Kodi may ask for Windows credentials. Use the account password, not a Windows Hello PIN.

### Browse it from Kodi

On Xbox Kodi:

1. Open **Settings → File manager**.
2. Browse/add `smb://PC-NAME/KodiTransfer`.
3. If hostname discovery fails, use the printed IP form such as `smb://192.168.x.x/KodiTransfer`.
4. Kodi's **Profile directory** contains its user data, including skin/add-on settings and `addon_data/pvr.iptvsimple/`.

## Advanced fallback: patch an exported IPTV Simple instance file

Use this only if remote text entry is inconvenient or we specifically want to inspect/backup the add-on settings.

1. Copy the active `instance-settings-*.xml` from `Profile directory/addon_data/pvr.iptvsimple/` to `KodiTransfer/from-xbox/`.
2. On the PC run:

```powershell
.\tools\patch-iptvsimple-settings.ps1 .\output\kodi-transfer\from-xbox\instance-settings-N.xml
```

The patcher makes a timestamped backup, preserves unrelated settings and now defaults to:

- curated English M3U
- shared generated XMLTV EPG

You can still override `-PlaylistUrl` if you intentionally want a different generated playlist.

Patch only the active IPTV Simple instance. Do not blindly replace every `instance-settings-*.xml` file left by earlier tests.

## Stop the temporary SMB share

Double-click `tools\stop-kodi-transfer.cmd`, or run elevated PowerShell:

```powershell
.\tools\prepare-kodi-transfer.ps1 -RemoveShare
```

The local transfer folder remains unless you delete it manually.

## Recommended division of labour

- **Long URL entry:** PC → Kodi JSON-RPC helper.
- **Files/backups/skin config/keymaps/artwork:** temporary SMB share.
- **Normal live TV + EPG:** Kodi reads GitHub directly; PC off.
- **iPlayer/catch-up playback:** handled locally by Kodi add-ons; PC off.
- **Stream-health audit:** optional PC maintenance with `tools/validate_streams.py`.

This keeps the Xbox setup convenient without turning the PC into a permanent IPTV server.
