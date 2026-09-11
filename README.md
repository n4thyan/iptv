# IPTV / Kodi playlist project

Clean IPTV source, EPG generation and maintenance tooling for a Kodi-on-Xbox setup.

For the quickest current-state handoff, see [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md).

## Main Kodi source

The main playlist is IPTV-org's English-language worldwide list:

`https://iptv-org.github.io/iptv/languages/eng.m3u`

The repository builds its own cleaned copy from that source rather than requiring thousands of channels to be maintained manually. It also generates a smaller cleaned UK-only playlist as an optional alternative.

Kodi-facing files are published from the `generated` branch:

- Full English playlist: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- Optional UK-only playlist: `https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u`
- EPG: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`
- EPG coverage report: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-coverage.txt`
- EPG generation stats: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-stats.json`
- Playlist build stats: `https://raw.githubusercontent.com/n4thyan/iptv/generated/playlist-stats.json`
- EPG batch/retry summary: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-chunk-summary.txt`
- Last successful generation time: `https://raw.githubusercontent.com/n4thyan/iptv/generated/last-update.txt`

Both generated M3Us embed the same EPG URL in their `x-tvg-url` header for clients that support it.

## Automatic UK group

The full `english.m3u` keeps all of IPTV-org's normal category groups, but the build also compares it with IPTV-org's UK country playlist and appends a `UK` group to matching channels.

That means Kodi can expose a real **UK** PVR group while still keeping the full worldwide English list. You do **not** need a second IPTV Simple configuration just to get UK channels, so there is no reason to duplicate those channels in `All channels`.

The smaller `uk.m3u` still exists for devices where you want only the UK list.

## What the automatic build does

The GitHub Actions workflow:

1. downloads the current English and UK IPTV-org playlists,
2. removes adult/NSFW entries using IPTV-org channel metadata plus a conservative fallback filter,
3. preserves `tvg-id`, logos, existing channel groups, stream URLs and Kodi/VLC stream directives,
4. tags English-playlist entries that also exist in the UK country feed with the extra `UK` group,
5. builds a compact channel metadata catalog from IPTV-org names and aliases,
6. maps EPG sources by exact `xmltv_id`, safe same-channel feed aliases, then safe **unique exact-name** matches for upstream definitions whose `xmltv_id` is blank,
7. records every ranked alternate guide source for each channel,
8. downloads the first-choice guide in small memory-safe batches,
9. retries failed batches channel-by-channel,
10. detects channels that still have no programmes and runs up to two additional passes using their next-ranked EPG providers,
11. merges all successful XMLTV fragments and produces guide statistics,
12. validates and publishes the finished files to the `generated` branch.

A second Actions workflow verifies the published branch after a successful generation run by reopening the compressed XMLTV guide, checking both playlists, verifying the generated UK group and cross-checking the generated statistics.

The generation workflow runs daily and can also be started manually. A failed generation does not overwrite the last good `generated` branch because publishing only happens after the validation steps pass.

## EPG coverage

The target is the **entire English playlist**, not just UK channels. IPTV-org's EPG tooling is the primary source because its `xmltv_id` identifiers align with the `tvg-id` values used by the IPTV-org playlist.

Coverage is intentionally conservative. The build now uses three mapping levels:

- exact playlist/EPG IDs;
- another feed belonging to the same IPTV-org base channel;
- an EPG definition with a blank `xmltv_id` only when its normalized channel name exactly matches one unique IPTV-org name/alias in our playlist and that base channel has only one playlist feed.

It does **not** fuzzy-match vaguely similar channel names or copy a generic schedule across several regional variants. Wrong guide data is worse than a blank row.

The ranked source manifest also lets the build try alternate providers when the first correctly-mapped provider returns no programmes. Two fallback passes are attempted before a channel is left blank.

Not every public IPTV channel has real schedule data available. The build therefore produces `epg-coverage.txt` showing exact matches, safe same-channel aliases, safe name-based mappings and channels for which no compatible source is known. Missing guide data is not fabricated.

If an EPG source crashes or exhausts memory, the build records isolated failures in `epg-failures.txt` rather than failing the entire guide. `epg-chunk-summary.txt` records primary/fallback selection and retry results, while `guide-stats.json` records how many XMLTV channels and programmes actually reached the finished guide.

The `XMLTV/xmltv` project remains useful as a standards/tooling reference for sorting, filtering, checking and merging XMLTV data, but it is not itself a universal listings database. The current generator therefore prioritizes real mapped guide providers rather than treating XMLTV tooling as a source of programme data.

See [`docs/EPG.md`](docs/EPG.md) for the architecture and [`docs/KODI_SETUP.md`](docs/KODI_SETUP.md) for the Xbox setup.

## Adult channels

The old custom adult/call-in playlist has been removed because those streams were not working reliably. Generated playlists also filter channels that IPTV-org marks as NSFW/adult, with a small fallback filter for obvious adult naming when metadata is missing.

## Dead-stream cleanup

Do **not** remove a stream after one failed HTTP request. IPTV streams can be temporarily unavailable, geo-blocked, rate-limited or require headers that a simplistic checker does not send.

`tools/validate_streams.py` provides a conservative local health check using `ffprobe`. It is intentionally designed to run from the same network as the Xbox rather than from GitHub's cloud runners, so region-restricted streams are not falsely classified as dead.

It classifies streams as:

- working,
- access/geo restricted,
- temporarily failed,
- dead,
- untested Kodi web-scraper entries.

Even hard 404/410 results need repeated consecutive failed validation runs before removal. A working, restricted or deliberately untested result breaks that failure streak. See [`docs/STREAM_VALIDATION.md`](docs/STREAM_VALIDATION.md).

## PC-assisted Xbox setup

The PC is **not** the permanent IPTV server. It is only used to avoid typing long URLs/controller text on the Xbox and for later maintenance.

The repository includes:

- `tools/prepare-kodi-transfer.ps1` — creates a temporary Windows SMB transfer pack/share;
- `tools/patch-iptvsimple-settings.ps1` — patches an exported IPTV Simple `instance-settings-*.xml` with the generated M3U and EPG URLs while preserving the rest of the configuration;
- [`docs/PC_TO_KODI.md`](docs/PC_TO_KODI.md) — the complete copy-out / patch / copy-back procedure.

After the patched settings file is copied back into Kodi and Kodi is restarted, the Xbox reads the playlist and guide from GitHub. The PC can be switched off.

## Other source references

| Purpose | URL |
|---|---|
| UK-only | `https://iptv-org.github.io/iptv/countries/uk.m3u` |
| Western Europe | `https://iptv-org.github.io/iptv/regions/wer.m3u` |
| English worldwide | `https://iptv-org.github.io/iptv/languages/eng.m3u` |

## Kodi

Kodi on Xbox uses **PVR IPTV Simple Client**. The normal configuration is:

- **M3U playlist URL** → generated `english.m3u`
- **XMLTV URL** → generated `guide.xml.gz`

After import, the source categories remain available and the generated **UK** group should appear alongside them. Favourites can then be managed in Kodi without editing the generated files.

If the full worldwide list feels too large, switch only the M3U URL to generated `uk.m3u`; it uses the same guide URL.

The PC is not required for normal playback or EPG use. It is only needed for setup, development and optional local stream-health audits.

## Project philosophy

Keep the setup lightweight and understandable: stock Kodi, official/known components, direct playlist/EPG data and small purpose-built tools. No giant third-party Kodi builds or mystery repository bundles.
