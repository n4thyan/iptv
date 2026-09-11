# PC → Xbox Kodi setup/maintenance

The PC is a **setup and maintenance tool**, not a server that must stay on.

Normal Xbox playback should continue to use the generated GitHub endpoints:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- EPG: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

That means the PC can be switched off after setup.

## Why use the PC at all?

Typing long URLs with an Xbox controller is slow. Kodi's File Manager can copy files between the Xbox Kodi profile and an SMB/Windows share, so we can export the existing IPTV Simple instance settings, patch them on the PC, and copy them back.

This is also useful later for keymaps, skin configuration backups, custom logos, and other small Kodi files.

## 1. Prepare a temporary Windows share

Open PowerShell **as Administrator** in the repository and run:

```powershell
.\tools\prepare-kodi-transfer.ps1 -CreateShare
```

The script:

- creates `output\kodi-transfer\`;
- downloads the current generated playlist/guide and diagnostics for inspection;
- creates `from-xbox\` and `to-xbox\` folders;
- prints the SMB hostname/IP path for Kodi;
- creates a temporary SMB share named `KodiTransfer` using the current Windows account.

Kodi may ask once for the Windows account credentials. Let Kodi save them.

The script does **not** enable insecure guest SMB access or open an anonymous write share.

## 2. Copy the active IPTV Simple settings file to the PC

On Xbox Kodi:

1. Open **Settings → File manager**.
2. In one pane browse the PC share, e.g. `smb://PC-NAME/KodiTransfer`.
3. In the other pane browse **Profile directory**, then:
   `addon_data/pvr.iptvsimple/`
4. Locate the active `instance-settings-*.xml` file for the configuration we want to keep.
5. Copy that one file to `KodiTransfer/from-xbox/`.

Kodi stores add-on user data under `special://profile/addon_data/`. Do not replace every instance file just because several are present; we already created more than one IPTV Simple configuration during testing.

## 3. Patch the exported settings on the PC

Run:

```powershell
.\tools\patch-iptvsimple-settings.ps1 .\output\kodi-transfer\from-xbox\instance-settings-N.xml
```

The patcher:

- creates a timestamped backup beside the file;
- preserves unrelated IPTV Simple settings;
- switches M3U location to remote URL mode;
- sets the generated full-English playlist URL;
- switches EPG location to remote URL mode;
- sets the generated XMLTV URL;
- keeps M3U/EPG caching enabled.

If we later decide to use only the UK playlist, run it with:

```powershell
.\tools\patch-iptvsimple-settings.ps1 `
  .\output\kodi-transfer\from-xbox\instance-settings-N.xml `
  -PlaylistUrl "https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u"
```

## 4. Copy the patched file back to Kodi

In Kodi File Manager:

1. Open `KodiTransfer/from-xbox/` in one pane.
2. Open `Profile directory/addon_data/pvr.iptvsimple/` in the other.
3. Copy the patched file back over the original file with the same name.
4. Fully quit Kodi from the Xbox dashboard.
5. Reopen Kodi and allow PVR Manager to reload.

Then open **TV → Guide**.

The PC is no longer needed once the file is copied back because the saved URLs point at GitHub, not the PC.

## 5. Remove the temporary share

When finished, from an elevated PowerShell run:

```powershell
.\tools\prepare-kodi-transfer.ps1 -RemoveShare
```

The local transfer folder remains on the PC unless you delete it manually.

## Alternative: manual file-only transfer

If we do not want to patch IPTV Simple's XML directly, the SMB share can still be used as a normal file shuttle. Kodi File Manager supports copying files from SMB into the profile directory. This is useful for keymaps, custom images and configuration backups.

## Safety rules

- Always keep the patcher's timestamped backup until Kodi has restarted successfully.
- Patch only the active IPTV Simple instance, not every instance file.
- Do not make the PC the permanent M3U/EPG host; the generated GitHub files are the always-on source.
- If Kodi fails after replacing an instance file, restore the `.backup-YYYYMMDD-HHMMSS` copy and restart Kodi.
