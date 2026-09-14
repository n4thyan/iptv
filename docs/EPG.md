# EPG architecture for Kodi

## Goal

Provide a useful programme guide for the generated Kodi playlists on Xbox without requiring a PC to stay online and without slow channel-by-channel scraping.

Current public endpoints:

- curated English + FAST M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u`
- curated UK M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-uk.m3u`
- full English + FAST M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- full UK M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u`
- XMLTV guide: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`
- coverage: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-coverage.txt`
- guide stats: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-stats.json`
- failures: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-failures.txt`

## Production approach

The production guide is built only from maintained prebuilt XMLTV feeds listed in `epg-feeds.txt`.

The workflow:

1. downloads current IPTV-org English and UK playlists;
2. removes adult/NSFW entries conservatively;
3. appends maintained FAST playlists for Samsung TV Plus GB, Pluto TV GB, Plex TV GB and Roku;
4. gives FAST entries an additional service group while preserving their original genre group;
5. preserves channel IDs, logos, stream URLs and Kodi/VLC directives;
6. downloads configured XMLTV feeds concurrently, including the matching FAST-service guides;
7. matches exact IDs first and uses only explicit conservative compatibility rules for known namespace differences;
8. rewrites compatible XMLTV IDs to the exact playlist `tvg-id` values when required;
9. de-duplicates programme rows;
10. builds `curated.m3u` and `curated-uk.m3u` from entries that actually have programme rows;
11. validates the generated outputs before publishing;
12. runs a separate verification workflow against the published `generated` branch.

The old provider-by-provider scraper, batching, fallback-selection and XMLTV-fragment scripts have been removed from `main`.

## FAST-service guide sources

The appended FAST playlists use service-native IDs. Matching XMLTV sources are therefore included directly:

- Samsung TV Plus GB → `https://i.mjh.nz/SamsungTVPlus/gb.xml.gz`
- Pluto TV GB → `https://i.mjh.nz/PlutoTV/gb.xml.gz`
- Plex TV GB → `https://i.mjh.nz/Plex/gb.xml.gz`
- Roku → `https://i.mjh.nz/Roku/all.xml.gz`

This is preferable to trying to map these services onto unrelated IPTV-org IDs.

## Compatibility matching

The fast builder is intentionally conservative. It supports exact IDs, explicitly known punctuation/quality variants, known EPGShare dataset suffixes, and known UK regional aliases. It does **not** perform broad fuzzy matching across countries or ambiguous channel families.

Wrong guide data is worse than missing guide data.

## Coverage

The 2026-09-11 pre-FAST checkpoint had 352 channels with programme data and 37,738 programme rows from 19 successful feeds. Those numbers are historical only; the current generated build is authoritative because FAST services now expand both the requested ID set and EPG sources.

Use `guide-stats.json` and the playlist-stat files on the `generated` branch for live figures after each build.

## Diagnostics

Generated diagnostics:

- `guide-stats.json` — global counts plus per-source results
- `epg-coverage.txt` — matched and unmatched playlist IDs
- `epg-failures.txt` — source download/parse failures
- `curated-playlist-stats.json`
- `curated-uk-playlist-stats.json`
- `playlist-stats.json`
- `uk-playlist-stats.json`
- `last-update.txt`

## Kodi setup

Normal configuration:

1. M3U → `curated.m3u`
2. XMLTV → `guide.xml.gz`
3. fully restart Kodi after changing PVR settings
4. allow PVR Manager to finish importing
5. open **TV → Guide**

For a UK-only installation, use `curated-uk.m3u` with the same guide.

The PC is not required for normal playback. It is only used for setup, maintenance, optional stream validation and moving Kodi configuration files when convenient.
