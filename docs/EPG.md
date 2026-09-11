# EPG architecture for Kodi

## Goal

Provide a useful programme guide for the generated Kodi playlists on Xbox without requiring a PC to stay online and without spending hours scraping channel-by-channel providers.

Current public endpoints:

- curated English M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u`
- curated UK M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-uk.m3u`
- full English M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- full UK M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u`
- XMLTV guide: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`
- coverage: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-coverage.txt`
- guide stats: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-stats.json`
- failures: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-failures.txt`

## Production approach

The production guide is built from the curated prebuilt XMLTV sources in `epg-feeds.txt`.

The workflow:

1. downloads current IPTV-org English and UK playlists;
2. removes adult/NSFW entries conservatively;
3. preserves channel IDs, logos, groups, stream URLs and Kodi/VLC directives;
4. downloads configured prebuilt XMLTV feeds concurrently;
5. matches source XMLTV IDs to playlist IDs using exact matches first;
6. applies only explicit conservative compatibility rules when providers encode the same channel differently;
7. rewrites matched XMLTV channel/programme IDs to the exact playlist `tvg-id` values;
8. de-duplicates programme rows;
9. emits one shared `guide.xml` / `guide.xml.gz`;
10. builds `curated.m3u` and `curated-uk.m3u` from entries that actually have programme rows;
11. validates the generated outputs before publishing;
12. runs a separate verification workflow against the published generated branch.

The old `iptv-org/epg` provider-by-provider scraper scripts remain in the repository for optional research/enrichment work, but they are no longer part of the normal production build.

## Compatibility matching

The fast builder is intentionally conservative.

It supports:

- exact playlist/source IDs;
- punctuation differences such as `Channel.4.HD.uk` versus `Channel4.uk`;
- quality suffix differences such as HD/SD where the normalized channel remains unambiguous;
- explicit known provider dataset suffixes, for example EPGShare US and Canada dataset namespaces;
- explicit known UK regional abbreviations.

It does **not** perform general fuzzy-name matching across countries or ambiguous channel families. If a normalized key could point to more than one different base channel, it is rejected.

Wrong guide data is worse than missing guide data.

## Current coverage philosophy

The project does not attempt 100% coverage. Some streams have no public schedule, some provider IDs do not map safely, and some large feeds are not worth forcing through unsafe heuristics.

The curated playlist is therefore the normal Kodi source: it contains only channels with real programme rows in the current generated guide.

After the Canada pass on 2026-09-11, the verified build had:

- 2,987 requested playlist IDs
- 352 channels with programmes
- 37,738 programme rows
- 19 configured feeds
- 19 downloaded feeds
- 0 feed failures

Country contributions included useful matched data from the UK, US, Canada, India, Australia and New Zealand, along with smaller contributions from several other configured feeds.

Use `guide-stats.json` for the live figures after each scheduled build.

## Diagnostics

Generated branch diagnostics:

- `guide-stats.json` — global counts plus per-source results
- `epg-coverage.txt` — matched and unmatched playlist IDs
- `epg-failures.txt` — source download/parse failures
- `curated-playlist-stats.json` — curated English playlist stats
- `curated-uk-playlist-stats.json` — curated UK playlist stats
- `playlist-stats.json` / `uk-playlist-stats.json` — full playlist stats
- `last-update.txt` — generation timestamp

The retired slow pipeline's `epg-chunk-summary.txt` is no longer generated.

## Kodi setup

Normal configuration:

1. M3U → `curated.m3u`
2. XMLTV → `guide.xml.gz`
3. fully restart Kodi after changing PVR settings
4. allow PVR Manager to finish importing
5. open **TV → Guide**

For a UK-only installation, use `curated-uk.m3u` with the same guide.

The PC is not part of normal playback. It is only used for setup, maintenance, optional stream validation and moving Kodi configuration files when convenient.

## XMLTV tooling

The XMLTV project remains useful for standards validation, filtering, sorting and provider-specific tooling. It is not a universal listings database, so installing XMLTV alone does not solve unmatched channels.

The generated guide is ordinary XMLTV and can be post-processed later if a specific reliable use case appears.
