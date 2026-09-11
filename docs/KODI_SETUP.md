# Kodi on Xbox — final IPTV setup

These steps are for the generated playlist/EPG, not the raw upstream URLs.

## 1. Open IPTV Simple Client

In Kodi:

**Add-ons → My add-ons → PVR clients → IPTV Simple Client → Configure**

Edit the main enabled configuration.

## 2. Choose the playlist

For the full English-language worldwide list, use:

`https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`

For a much smaller UK-only list, use:

`https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u`

Under **General** set:

- Location: **Remote path (Internet address)**
- M3U playlist URL: one of the URLs above

Both generated playlists point at the same guide and preserve IPTV-org `tvg-id`, logo, group and stream-option metadata.

## 3. EPG

Under **EPG** set:

- Location: **Remote path (Internet address)**
- XMLTV URL:

`https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

Save the configuration.

## 4. Reload Kodi

Fully quit Kodi from the Xbox dashboard, then reopen it. Allow PVR Manager time to import the playlist and EPG.

Open:

**TV → Guide**

The playlist and XMLTV guide use the same IPTV-org channel IDs, so matching happens by `tvg-id` rather than by fuzzy channel names.

## 5. If the guide is empty or looks stale

Before changing URLs, check the generated build status/files:

- `https://raw.githubusercontent.com/n4thyan/iptv/generated/last-update.txt`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-stats.json`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-chunk-summary.txt`

If those are current, fully restart Kodi. If necessary, clear PVR/EPG data from Kodi's PVR settings and let IPTV Simple import the playlist and guide again.

Some channels legitimately have no programme data because IPTV-org has no compatible EPG source for that `tvg-id`. The project records those in `epg-coverage.txt` instead of inventing schedules.

## 6. If a channel does not play

Do not assume the whole playlist is broken. Public IPTV streams can be temporarily unavailable, geo-restricted or require specific request headers. The generated playlist preserves IPTV-org's stream directives.

For a systematic cleanup from the same network as the Xbox, use the local validator documented in [`STREAM_VALIDATION.md`](STREAM_VALIDATION.md). It requires repeated failures before removing a stream.

## Later UI work

Once this data layer is stable, the next Kodi-side jobs are:

1. UK and favourite channel groups,
2. sensible channel ordering,
3. logos/artwork cleanup,
4. remote/controller key mapping,
5. Sky+/Sky-Q-style skin/guide layout,
6. catch-up/live-TV integrations where they can be added cleanly.
