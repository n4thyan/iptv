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

### Recommended choice

Use the full generated `english.m3u` unless you specifically want a UK-only installation.

The full playlist automatically adds a **UK** PVR group to channels that also appear in IPTV-org's UK country feed while preserving the normal Movies, News, Entertainment, Kids and other source groups.

Do **not** add a second IPTV Simple configuration solely for the UK playlist if you are already using `english.m3u`; that would duplicate UK channels in **All channels**. The generated UK group is designed to avoid that.

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

When using the full playlist, cycle the guide's channel group selector and you should see **UK** alongside the original IPTV categories. This group comes from the generated M3U and does not need to be populated manually in Kodi's Group Manager.

## 5. Favourites

Keep favourites as a Kodi-side choice rather than baking them into the generated playlist. That way daily playlist refreshes cannot overwrite your personal selection.

Use Kodi's normal favourite/channel-group controls for the handful of channels you actually use most often.

## 6. If the guide is empty or looks stale

Before changing URLs, check the generated build status/files:

- `https://raw.githubusercontent.com/n4thyan/iptv/generated/last-update.txt`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-stats.json`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-chunk-summary.txt`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/playlist-stats.json`

If those are current, fully restart Kodi. If necessary, clear PVR/EPG data from Kodi's PVR settings and let IPTV Simple import the playlist and guide again.

Some channels legitimately have no programme data because IPTV-org has no compatible EPG source for that `tvg-id`. The project records those in `epg-coverage.txt` instead of inventing schedules.

## 7. If a channel does not play

Do not assume the whole playlist is broken. Public IPTV streams can be temporarily unavailable, geo-restricted or require specific request headers. The generated playlist preserves IPTV-org's stream directives.

For a systematic cleanup from the same network as the Xbox, use the local validator documented in [`STREAM_VALIDATION.md`](STREAM_VALIDATION.md). It requires repeated failures before removing a stream.

## 8. What still belongs on the Kodi side

The data layer is separate from presentation. Once the generated playlist and guide are stable, Kodi-side work can be done without changing the generation pipeline:

1. choose favourite channels,
2. adjust channel ordering where useful,
3. clean up any logos/artwork that look poor,
4. map the Xbox controller/TV remote,
5. install/tune a Sky+/Sky-Q-style skin or guide layout,
6. add catch-up and radio integrations where they can be done cleanly.

The PC is not required for ordinary viewing. It is only needed for maintenance, development and optional local stream-health checks.
