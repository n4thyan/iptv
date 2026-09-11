# Project status / handoff

This is the current checkpoint for the Kodi-on-Xbox IPTV project.

## Data layer: stable

The production path is now the fast prebuilt-feed pipeline. The old provider-by-provider scraper remains in the repository only as optional research/enrichment tooling and is not part of the normal daily build.

Recommended Kodi endpoints:

- Curated English playlist: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u`
- Curated UK-only playlist: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-uk.m3u`
- Shared XMLTV guide: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

Broader playlists remain available when needed:

- Full English: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- Full UK: `https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u`

The curated playlists are the normal choice because they contain only playlist entries that currently have real programme rows in the generated XMLTV.

## Current verified build

The build after Canada support was added completed successfully and the independent generated-output verifier also passed.

At that checkpoint:

- source English playlist IDs: 2,987
- channels with programme data: 352
- programme rows: 37,738
- EPG feeds configured/downloaded: 19 / 19
- EPG feed failures: 0
- curated English entries: 352
- curated UK entries: 64

Useful country contributions included:

- US: 157 matched channel elements / 16,870 programmes
- Canada: 23 / 2,052
- India: 45 / 1,699
- Australia: 13 / 2,537
- New Zealand: 9 / 914

These numbers are not hard-coded promises; `guide-stats.json` and the curated playlist stats on the `generated` branch are authoritative after every refresh.

## Production EPG behavior

The builder downloads the maintained sources in `epg-feeds.txt` concurrently. It first accepts exact playlist IDs and then applies only explicit conservative compatibility rules such as punctuation/quality differences, known EPGShare dataset suffixes and known UK regional aliases. Country boundaries and ambiguous collisions are preserved rather than guessed across.

The final XMLTV channel/programme IDs are rewritten to the exact `tvg-id` values used by the playlist so Kodi can join the guide automatically.

The production build does not chase every unmatched channel. A blank/unavailable channel is preferred over attaching the wrong schedule.

## Generated diagnostics

Current generated diagnostics are:

- `guide-stats.json`
- `epg-coverage.txt`
- `epg-failures.txt`
- `playlist-stats.json`
- `uk-playlist-stats.json`
- `curated-playlist-stats.json`
- `curated-uk-playlist-stats.json`
- `last-update.txt`

The old `epg-chunk-summary.txt` output belonged to the retired slow scraping pipeline and is no longer produced.

## Kodi / Xbox setup

Keep one PVR IPTV Simple Client configuration for normal use:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u`
- XMLTV: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

If a UK-only installation is wanted, switch the M3U to `curated-uk.m3u` and keep the same EPG.

The PC remains a setup/maintenance workstation only. Kodi reads the GitHub endpoints directly, so the PC does not need to stay on.

The helper scripts in `tools/` now default to the curated playlist and still expose the full playlists as optional choices.

## Stream health

Stream validation stays separate from playlist generation. `tools/validate_streams.py` should be run from the same network as the Xbox when a cleanup is wanted. Do not delete a channel because one cloud or HTTP probe fails; geo-blocks, headers and temporary upstream faults can make working streams look dead.

## Kodi-side phase now

The backend is no longer the blocker. The next work is Kodi presentation and service integration:

1. tune the installed Sky/Sky-Q-style skin and guide layout;
2. set useful channel numbering, groups and favourites;
3. integrate BBC iPlayer/catch-up entry points into the TV / Videos / Movies navigation where the installed skin permits custom menu items/widgets;
4. add other legitimate broadcaster catch-up services only where they work reliably on Xbox Kodi;
5. polish remote/controller navigation so it behaves like a TV appliance rather than a generic media centre.

BBC iPlayer is already working as an add-on on the Xbox, so the next step is menu/library-style integration rather than basic playback setup.

## If something looks wrong

Check in this order:

1. `last-update.txt` is current;
2. `guide-stats.json` reports downloaded sources, matched channels and programme rows;
3. `curated-playlist-stats.json` reports a non-zero `entries_kept` value;
4. `epg-coverage.txt` shows matched/unmatched playlist IDs;
5. `epg-failures.txt` explains any feed download/parse failures;
6. fully restart Kodi;
7. only then clear/reload Kodi PVR/EPG data if necessary.

Do not fall back to the retired multi-hour scraping path merely because some channels remain unmatched.
