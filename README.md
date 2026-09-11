# IPTV / Kodi project

Kodi-on-Xbox IPTV playlist and EPG tooling, designed to stay lightweight and usable without leaving a PC running.

## Recommended Kodi setup

Use the generated **curated** playlist for normal TV viewing:

- Curated English playlist: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u`
- Curated UK-only playlist: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-uk.m3u`
- EPG: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

The curated playlists contain only channels whose final playlist `tvg-id` has real programme rows in the generated XMLTV guide. This avoids filling Kodi's guide with thousands of blank rows.

The broader source playlists are still published when you want to browse everything:

- Full English playlist: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- Full UK playlist: `https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u`

All generated M3Us embed the same EPG URL in their `x-tvg-url` header.

## Why the EPG pipeline changed

The first EPG implementation mapped the IPTV-org English playlist into `iptv-org/epg` and then scraped many guide providers channel-by-channel. It was accurate but far too slow for this project: a single primary pass could take well over an hour before fallback providers were attempted.

The production pipeline now consumes a curated set of **prebuilt XMLTV feeds**, matches them to IPTV-org channels using exact IDs plus deliberately conservative known compatibility rules, de-duplicates programme rows, rewrites matched data to the playlist's exact `tvg-id` values, and publishes only channels with real programme data. The slow provider scraper scripts remain in the repository as research/enrichment tools, but they no longer block the daily Kodi build.

`epg-feeds.txt` contains the maintained feed list. It prioritizes the UK and other English-speaking countries, plus selected international coverage useful for this setup.

## Automatic build

`.github/workflows/update-generated.yml` runs daily and on relevant changes. It has a 30-minute hard ceiling and:

1. downloads IPTV-org's current English and UK playlists;
2. removes adult/NSFW entries conservatively;
3. preserves stream URLs, logos, IDs, channel groups and Kodi/VLC directives;
4. appends a real `UK` group to matching entries in the full English list;
5. downloads the prebuilt XMLTV feeds listed in `epg-feeds.txt` in parallel;
6. keeps only programme data that can be mapped safely to current playlist `tvg-id` values;
7. rewrites XMLTV IDs to those exact playlist IDs and de-duplicates programme rows;
8. creates `curated.m3u` and `curated-uk.m3u` from channels that actually have programme data;
9. validates the playlists and guide before publishing;
10. force-refreshes the `generated` branch only after the build passes validation.

A failed build therefore does not intentionally replace the previous good generated output.

## Generated diagnostics

The `generated` branch also publishes:

- `guide-stats.json` — programme/channel counts and per-feed results;
- `epg-coverage.txt` — matched and unmatched playlist IDs;
- `epg-failures.txt` — feed download/parse failures, if any;
- `playlist-stats.json` and `uk-playlist-stats.json`;
- `curated-playlist-stats.json` and `curated-uk-playlist-stats.json`;
- `last-update.txt`.

Coverage is intentionally conservative. Wrong guide data is worse than a blank guide row, so ambiguous mappings are rejected instead of guessed.

## Main upstream playlist sources

| Purpose | URL |
|---|---|
| English worldwide | `https://iptv-org.github.io/iptv/languages/eng.m3u` |
| UK-only | `https://iptv-org.github.io/iptv/countries/uk.m3u` |
| Western Europe reference | `https://iptv-org.github.io/iptv/regions/wer.m3u` |

## Kodi on Xbox

Kodi uses **PVR IPTV Simple Client**.

For the normal setup:

- M3U playlist URL → generated `curated.m3u`
- XMLTV URL → generated `guide.xml.gz`

If you only want UK channels, change the M3U URL to `curated-uk.m3u` and keep the same XMLTV URL.

The PC is only a setup/maintenance workstation. It is not required for normal playback or EPG updates.

Useful helpers remain in `tools/` for sending long URLs to Kodi over JSON-RPC and for temporary SMB transfer/backup tasks. Those helpers now default to the curated playlist while retaining full-list options.

## Stream validation

Do not delete a stream because one HTTP probe fails. IPTV streams can be temporarily unavailable, geo-blocked, rate-limited or require headers.

`tools/validate_streams.py` is a conservative local health checker intended to run from the same network as the Xbox. Stream cleanup stays separate from playlist generation so transient outages do not silently destroy the maintained list.

## Next project phase

The backend is stable enough to stop chasing marginal EPG coverage. The next layer is presentation and service integration: tune the installed Sky/Sky-Q-style guide/navigation, organise channel numbering/groups/favourites, and integrate working catch-up services such as BBC iPlayer into the main Kodi TV / Videos / Movies experience where the skin permits custom menu items and widgets.
