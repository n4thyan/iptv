# EPG plan for Kodi

## Goal

Provide one programme guide for the cleaned English-language playlist used by Kodi on Xbox, without requiring a PC to stay online.

The generated files live on the repository's `generated` branch and are refreshed automatically by GitHub Actions.

Once the first successful build has populated that branch, Kodi can use these directly:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- XMLTV EPG: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`
- coverage report: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-coverage.txt`

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

1. Download `https://iptv-org.github.io/iptv/languages/eng.m3u`.
2. Download IPTV-org channel metadata.
3. Remove channels marked NSFW/adult by IPTV-org plus a small conservative fallback filter.
4. Preserve the remaining channel metadata, stream URLs, `tvg-id` values and Kodi/VLC stream directives.
5. Scan `iptv-org/epg` channel definitions for compatible `xmltv_id` values.
6. Prefer an English-language guide source where multiple sources are available.
7. Use a same-channel feed alias where it is safe and useful.
8. Build one custom `epg.channels.xml` describing only the channels required by our playlist.
9. Split that large request into small channel batches. The upstream Node grabber exhausted its default heap when all ~1.4k matched channels were queued in one process, so chunking resets memory between batches.
10. Grab two days of schedule data for each batch. A failed batch is recorded rather than destroying successful output from every other batch.
11. Merge all valid XMLTV fragments into one `guide.xml`.
12. Validate that the final guide contains actual `<programme>` records, gzip it and publish it alongside the cleaned M3U.

At the first mapping test the IPTV-org EPG definitions covered roughly half of the nearly 3,000 English playlist channel IDs. That is a source-data limitation, not a Kodi limitation. We can later use XMLTV grabbers or other legitimate listing sources to improve the unmatched half where real schedule data exists.

## Kodi setup

After the generated files exist:

1. Open **Add-ons > My add-ons > PVR clients > IPTV Simple Client > Configure**.
2. Edit the main enabled configuration.
3. Under **General**, set the M3U playlist URL to the generated `english.m3u` URL above.
4. Under **EPG**, set the XMLTV URL to the generated `guide.xml.gz` URL above.
5. Save, fully quit Kodi and reopen it.
6. Open **TV > Guide** and let PVR Manager finish importing data.

A shorter Xbox-focused walkthrough is in [`KODI_SETUP.md`](KODI_SETUP.md).

## Stream validation

Stream validation is intentionally separate from EPG generation. A stream must not be deleted merely because one probe fails: public IPTV streams can be temporarily offline, geo-blocked, rate-limited, or reject a probe method while still working in Kodi.

The local validator keeps state across runs and classifies streams as:

- working,
- access/geo restricted,
- temporarily failed,
- repeatedly failed / likely dead,
- untestable Kodi web-scraper entries.

Only streams that meet the conservative removal threshold are omitted from its validated output. See [`STREAM_VALIDATION.md`](STREAM_VALIDATION.md).
