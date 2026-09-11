# Project status / handoff

This file is the quick checkpoint for the Kodi-on-Xbox IPTV project.

## Data pipeline: complete

The repository owns the normal Kodi data flow instead of pointing Kodi directly at raw upstream files.

Final public endpoints after a successful generation run:

- Full English playlist: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- UK-only playlist: `https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u`
- Shared XMLTV guide: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`
- Generation timestamp: `https://raw.githubusercontent.com/n4thyan/iptv/generated/last-update.txt`
- Guide stats: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-stats.json`
- EPG coverage: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-coverage.txt`
- EPG primary/fallback summary: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-chunk-summary.txt`
- Isolated EPG failures: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-failures.txt`

The full English playlist is the recommended Xbox source. It preserves IPTV-org's normal categories and automatically adds a `UK` group for channels also present in IPTV-org's UK country feed. This avoids creating a duplicate second PVR configuration merely to get a UK group.

## Automated EPG maintenance: expanded

The EPG pipeline now does more than the original 1,448-ID baseline mapping.

GitHub Actions:

1. fetches fresh upstream English and UK playlists;
2. filters IPTV-org NSFW/adult channels plus a conservative fallback filter;
3. preserves channel IDs, logos, groups and Kodi/VLC stream directives;
4. adds the generated `UK` group to matching English-playlist channels;
5. builds a channel metadata catalog from IPTV-org names and aliases;
6. maps guide providers in this order: exact `xmltv_id`, same IPTV-org base-channel feed, then a safe unique exact-name match for otherwise-unmapped definitions;
7. records multiple ranked provider candidates for each channel where available;
8. grabs the primary guide in memory-safe batches;
9. retries failed batches one channel at a time;
10. identifies mapped channels that still have no programme records;
11. tries the next-ranked EPG provider for those channels;
12. repeats once more with a third provider where available;
13. merges every successful XMLTV fragment;
14. validates playlists and real programme records;
15. publishes only after validation succeeds;
16. independently reopens and verifies the published `generated` branch.

A failed run therefore leaves the previous known-good `generated` branch in place.

The pipeline still does not claim 100% EPG coverage. Some public channels simply do not have a usable listings source. The current `epg-coverage.txt` and `guide-stats.json` are authoritative after each build; missing schedules are not fabricated.

## XMLTV/xmltv

The XMLTV project is useful as a standards/tooling layer for sorting, checking, filtering and merging XMLTV and for provider-specific grabbers. It is not itself a universal programme database, so the project does not treat installing XMLTV as a way to magically fill every channel.

The generated guide is ordinary XMLTV and can be run through XMLTV utilities later if a specific extra grabber or post-processing step becomes worthwhile.

## Stream health: complete as a maintenance tool

`tools/validate_streams.py` can be run from the same UK network as the Xbox with `ffprobe`. It deliberately does not run as a destructive cloud cleanup because region restrictions and temporary upstream faults can make good streams look dead from GitHub runners.

A stream is only removed from the validator's cleaned output after repeated consecutive failures. Working, access-restricted and deliberately untestable Kodi scraper entries reset the failure streak.

See `docs/STREAM_VALIDATION.md`.

## PC-assisted Xbox setup: ready

The PC is a one-time setup/maintenance workstation, **not** the permanent IPTV host.

Use:

```powershell
.\tools\prepare-kodi-transfer.ps1 -CreateShare
```

Then Kodi File Manager can copy the active `instance-settings-*.xml` file from `special://profile/addon_data/pvr.iptvsimple/` into the temporary Windows SMB share. On the PC patch that exported file with:

```powershell
.\tools\patch-iptvsimple-settings.ps1 .\output\kodi-transfer\from-xbox\instance-settings-N.xml
```

Copy the patched XML back over the same Kodi instance file and restart Kodi. The patcher writes the generated GitHub M3U/EPG URLs, so the PC can be turned off after setup.

Full instructions: `docs/PC_TO_KODI.md`.

When the transfer work is finished, remove the temporary share with:

```powershell
.\tools\prepare-kodi-transfer.ps1 -RemoveShare
```

## Xbox setup when returning

Keep **one** IPTV Simple Client configuration:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- XMLTV: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

Fully quit Kodi from the Xbox dashboard and reopen it. Let PVR Manager finish importing. In **TV > Guide**, use the group selector to check for the generated **UK** group.

Do not add the generated UK-only playlist as a second configuration unless duplicate UK channels in **All channels** are actually desired. If a UK-only installation is preferred instead, patch the main M3U URL to generated `uk.m3u`.

## Kodi-side work still intentionally separate

These are presentation/user-preference jobs rather than missing pieces of the playlist/EPG generator:

- choose personal favourite channels;
- optionally reorder/hide channels in Kodi;
- tune logos/artwork if individual sources look poor;
- configure the One For All remote/controller mapping;
- choose/tune a Sky+/Sky-Q-style skin/guide layout;
- add radio sources;
- add legitimate catch-up integrations such as BBC/iPlayer where reliable on Xbox Kodi.

The same temporary SMB workflow can be reused to move keymaps, backups and other small Kodi files without typing long paths on the Xbox.

## If something looks wrong

Check in this order:

1. `last-update.txt` is current;
2. `guide-stats.json` contains channels and programme records;
3. `playlist-stats.json` reports `extra_groups.UK.entries_tagged` greater than zero;
4. `epg-coverage.txt` shows how the channel IDs were mapped;
5. `epg-chunk-summary.txt` shows primary and alternate-provider attempts;
6. `epg-failures.txt` explains isolated upstream guide failures;
7. fully restart Kodi;
8. only then clear/reload Kodi PVR/EPG data if necessary.

Do not replace the generated URLs with raw upstream URLs just because one channel or one guide row is temporarily unavailable.
