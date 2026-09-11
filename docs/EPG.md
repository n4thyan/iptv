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

The PC is therefore only needed for setup/development/maintenance and optional stream-health audits, not for normal Kodi playback.

## Why IPTV-org/epg is the primary EPG engine

The English playlist comes from IPTV-org and carries `tvg-id` values. The `iptv-org/epg` project uses the same IPTV-org channel identifiers as its `xmltv_id` values, so it is the best starting point for matching guide data to the playlist.

The mapper now uses three conservative levels:

1. **Exact ID** — playlist `tvg-id` equals an EPG `xmltv_id`.
2. **Same-channel feed alias** — the source belongs to the same IPTV-org base channel but exposes a different feed/region suffix; the output ID is rewritten to the playlist target.
3. **Safe unique-name fallback** — for upstream EPG definitions with a blank `xmltv_id`, the displayed source name may be used only when it exactly normalizes to one unique IPTV-org channel name/alias in the current playlist, and that base channel has only one playlist feed.

The third mode deliberately does not perform loose fuzzy matching. Ambiguous names, very short generic names, and multi-feed regional channels are left unmatched unless there is an explicit ID-based definition.

## Ranked alternate providers

Correct mapping is only half the problem: an EPG provider can be temporarily broken or return no programmes even when its channel definition is correct.

`build_epg_channels.py` therefore writes a ranked source manifest for every playlist target. The workflow first grabs the best source. After merging that guide, it finds channels that still have **zero programme records** and tries the next-ranked provider. It can do this twice.

This produces three source attempts at most:

- primary source,
- fallback source #1,
- fallback source #2.

A fallback is only attempted for channels still lacking programmes, so channels that already have working guide data are not duplicated or overwritten needlessly.

## XMLTV/xmltv

`https://github.com/XMLTV/xmltv` is useful at the standards/tooling layer. It provides utilities such as sorting, filtering, checking and merging XMLTV data, plus provider-specific grabbers.

It is **not** a universal listings database by itself. Installing it would not magically fill every unmatched IPTV channel. The current project therefore uses actual mapped guide providers first and emits normal XMLTV that remains compatible with XMLTV tooling if we later need extra post-processing or a specific additional grabber.

## Current generation pipeline

1. Download the IPTV-org English playlist and, separately, the smaller UK playlist.
2. Download IPTV-org channel metadata.
3. Remove channels marked NSFW/adult by IPTV-org plus a small conservative fallback filter.
4. Preserve the remaining channel metadata, stream URLs, `tvg-id` values and Kodi/VLC stream directives.
5. Add the extra `UK` PVR group to English-playlist entries that also occur in the UK country feed.
6. Build `channel-catalog.json` containing playlist IDs plus IPTV-org channel names and alternate names.
7. Scan all `iptv-org/epg` channel definitions.
8. Build ranked EPG candidates using exact IDs, safe same-base feed aliases and safe unique exact-name mappings for otherwise-unmapped definitions.
9. Grab the first-choice sources in memory-safe batches.
10. If a batch fails, retry the affected channels one-by-one.
11. Merge the primary XMLTV and identify channels that still have no programme records.
12. Build a first alternate-source request for those channels and grab it with the same resilient batching/retry logic.
13. Merge again and repeat once more with the third-ranked provider where available.
14. Merge every successful fragment into the final `guide.xml`.
15. Produce `guide-stats.json`, `epg-coverage.txt`, fallback selection stats and failure diagnostics.
16. Validate the playlists and final guide, gzip the XMLTV and publish everything to `generated`.
17. After a successful build, a separate verification workflow checks out the published `generated` branch, reopens the gzip guide, validates both M3Us and cross-checks the statistics.

Before the safe-name and alternate-provider expansion, the mapper found definitions for **1,448 of 2,987** English-playlist IDs (1,196 exact plus 252 same-channel aliases). That is the historical baseline, not a promise about the final expanded count. The current generated `epg-coverage.txt` and `guide-stats.json` are the authoritative results after each build.

No workflow can honestly guarantee EPG for every public stream: some FAST/local/temporary channels do not publish usable schedules, and some public guide sites break. The project prefers a blank guide row over attaching the wrong programme schedule.

## Kodi setup

For the full worldwide English setup:

1. Use the generated `english.m3u` URL for the main IPTV Simple configuration.
2. Use the generated `guide.xml.gz` URL for XMLTV.
3. Fully quit Kodi and reopen it so PVR Manager reloads both.
4. Open **TV > Guide** and use the group selector for the generated **UK** group when required.

To avoid typing the long URLs on Xbox, use the PC-assisted workflow in [`PC_TO_KODI.md`](PC_TO_KODI.md): copy the active `instance-settings-*.xml` file to the PC over a temporary SMB share, patch the URLs there, and copy it back.

If the full playlist is too cumbersome on Xbox, the same patcher can switch the M3U URL to generated `uk.m3u`; it uses the same programme guide.

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
