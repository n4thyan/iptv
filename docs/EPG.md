# EPG plan for Kodi

## Goal

Provide one programme guide for the cleaned English-language playlist used by Kodi on Xbox, without requiring a PC to stay online.

The generated files live on the repository's `generated` branch and are refreshed automatically by GitHub Actions.

Kodi can use these directly:

- full English M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- optional UK-only M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u`
- XMLTV EPG: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`
- coverage report: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-coverage.txt`
- finished guide stats: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-stats.json`
- EPG batch/retry summary: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-chunk-summary.txt`
- isolated EPG failures: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-failures.txt`

The PC is therefore only needed for development/maintenance and optional stream-health audits, not for normal Kodi playback.

## Why IPTV-org/epg is the primary EPG engine

The English playlist comes from IPTV-org and carries `tvg-id` values. The `iptv-org/epg` project uses the same IPTV-org channel identifiers as its `xmltv_id` values, so it is the best starting point for matching guide data to the playlist.

The mapper first looks for an exact ID. If a playlist uses a base channel while a guide provider only exposes a regional/feed variant of the same IPTV-org channel, the mapper may safely use that same-channel feed as an alias and rewrite the guide output ID back to the playlist ID. It never fuzzy-matches unrelated channels just because their names look similar.

The build does not assume every channel has EPG coverage. A public stream can exist even when no reliable programme-listing source exists. `epg-coverage.txt` therefore reports exact matches, same-channel aliases and genuinely unmatched IDs rather than inventing schedule data.

## XMLTV/xmltv

`https://github.com/XMLTV/xmltv` is also useful, but it solves a slightly different layer of the problem. It is a mature toolkit for obtaining, converting, filtering and post-processing XMLTV listings.

For this project the current plan is:

1. use `iptv-org/epg` first because its channel IDs align with the IPTV-org playlist,
2. emit standard XMLTV (`guide.xml` / `guide.xml.gz`) for Kodi,
3. bring in XMLTV/xmltv utilities later if we need more advanced merging, filtering, validation, time correction or extra country/provider grabbers to improve coverage.

This avoids adding a second toolchain before it is actually needed.

## Current generation pipeline

1. Download the IPTV-org English playlist and, separately, the smaller UK playlist.
2. Download IPTV-org channel metadata.
3. Remove channels marked NSFW/adult by IPTV-org plus a small conservative fallback filter.
4. Preserve the remaining channel metadata, stream URLs, `tvg-id` values and Kodi/VLC stream directives.
5. Scan `iptv-org/epg` channel definitions for compatible `xmltv_id` values required by the full English playlist.
6. Prefer an English-language guide source where multiple sources are available.
7. Use a same-channel feed alias where it is safe and useful.
8. Build one custom `epg.channels.xml` describing only matched channels.
9. Split the request into 20-channel primary batches. This keeps each Node grabber process small enough to avoid the heap exhaustion seen when much larger jobs were queued.
10. Grab two days of schedule data for each primary batch.
11. If a primary batch fails, split that exact batch into one-channel requests and retry them independently. A single broken provider/channel can therefore be isolated without throwing away the other channels from the batch.
12. Record the final isolated failures in `epg-failures.txt` and batch/retry totals in `epg-chunk-summary.txt`.
13. Merge all successful XMLTV fragments into one `guide.xml`.
14. Produce `guide-stats.json` from the merged guide, including XMLTV channel and programme counts.
15. Validate the playlists and guide, gzip the XMLTV and publish everything to `generated`.
16. After a successful build, a separate verification workflow checks out the published `generated` branch, reopens the gzip guide, validates both M3Us and cross-checks the statistics.

The mapping layer currently finds EPG definitions for 1,448 of 2,987 English-playlist `tvg-id` values: 1,196 exact matches plus 252 same-channel feed aliases. The remaining 1,539 IDs have no compatible IPTV-org EPG definition at present. That is a source-data limitation, not a Kodi limitation, and missing schedules are not fabricated.

## Kodi setup

For the full worldwide English setup:

1. Open **Add-ons > My add-ons > PVR clients > IPTV Simple Client > Configure**.
2. Edit the main enabled configuration.
3. Under **General**, set the M3U playlist URL to the generated `english.m3u` URL above.
4. Under **EPG**, set the XMLTV URL to the generated `guide.xml.gz` URL above.
5. Save, fully quit Kodi and reopen it.
6. Open **TV > Guide** and let PVR Manager finish importing data.

If the full playlist is too cumbersome on Xbox, switch the M3U URL to generated `uk.m3u`. It embeds and uses the same programme-guide URL, so no second EPG is required.

A shorter Xbox-focused walkthrough is in [`KODI_SETUP.md`](KODI_SETUP.md).

## Stream validation

Stream validation is intentionally separate from EPG generation. A stream must not be deleted merely because one probe fails: public IPTV streams can be temporarily offline, geo-blocked, rate-limited, or reject a probe method while still working in Kodi.

The local validator keeps state across runs and classifies streams as:

- working,
- access/geo restricted,
- temporarily failed,
- hard not-found/gone,
- untestable Kodi web-scraper entries.

All actual removals still require repeated consecutive failed validation runs, including 404/410 responses. A successful, access-restricted or deliberately untested result resets the failure streak. See [`STREAM_VALIDATION.md`](STREAM_VALIDATION.md).
