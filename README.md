# IPTV / Kodi on Xbox

A lightweight Kodi-on-Xbox IPTV setup with an automatically generated M3U playlist and XMLTV guide. Normal playback and guide updates come directly from GitHub, so the PC does **not** need to remain switched on.

## Recommended Kodi setup

Use one **PVR IPTV Simple Client** instance:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u`
- XMLTV: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

For a UK-only setup use `curated-uk.m3u` instead and keep the same guide URL.

The curated playlist only keeps channels that currently have real programme rows in the generated XMLTV, so Kodi is not filled with thousands of blank guide entries.

The default `guide.xml.gz` is the **Xbox-optimised rolling guide**. It retains all programme-backed channels but trims old/far-future rows to reduce Kodi startup/import work. The untrimmed guide is still published as `guide-full.xml.gz` for desktop/testing use.

## What is in the main playlist

The build starts with IPTV-org's English-language playlist, filters adult/NSFW entries conservatively, adds useful grouping, and then appends maintained free ad-supported streaming television (FAST) services before the EPG pass.

Current FAST sources:

- **Samsung TV Plus — GB**
- **Pluto TV — GB**
- **Plex TV — GB**
- **Roku Channel — all-region source**

FAST entries receive an extra Kodi group such as `FAST - Samsung TV Plus` or `FAST - Pluto TV`, while retaining their original genre group as well. Duplicate stream URLs are skipped.

The FAST source playlists come from the maintained `BuddyChewChew/app-m3u-generator` project. Their matching XMLTV guides come from `i.mjh.nz`, allowing service-native `tvg-id` values to join directly without fuzzy guessing.

## EPG pipeline

The production guide uses the **fast prebuilt-feed path only**. The previous provider-by-provider scraper, batching, fallback-selector and XMLTV-fragment pipeline has been removed from `main`.

The current process is:

1. build the cleaned English playlist;
2. append Samsung TV Plus, Pluto TV, Plex TV and Roku FAST entries;
3. build the optional UK-only playlist;
4. download the maintained XMLTV feeds in `epg-feeds.txt` concurrently;
5. match exact IDs first and only apply explicitly defined conservative compatibility rules;
6. rewrite compatible XMLTV IDs to the exact playlist `tvg-id` where required;
7. de-duplicate programme rows;
8. create `curated.m3u` and `curated-uk.m3u` containing only channels with programme data;
9. generate both the full XMLTV and a rolling Xbox-optimised XMLTV window;
10. validate the output before replacing the `generated` branch.

Wrong guide data is considered worse than a missing guide row, so ambiguous matches are rejected rather than guessed.

## Published outputs

The `generated` branch is an **output branch**, not a development branch. It is force-refreshed automatically after a successful build.

Published files include:

- `curated.m3u` — recommended English + FAST playlist with EPG coverage;
- `curated-uk.m3u` — UK-only curated playlist;
- `english.m3u` — broader English + FAST playlist;
- `uk.m3u` — broader UK-only playlist;
- `guide.xml.gz` — Xbox-optimised rolling XMLTV guide (recommended);
- `guide-full.xml.gz` — untrimmed XMLTV guide;
- `guide-stats.json` — full-guide statistics;
- `xbox-guide-stats.json` — rolling-guide statistics;
- `epg-coverage.txt`;
- `epg-failures.txt`;
- playlist statistics;
- `last-update.txt`.

## Repository branches

`main` is the canonical source branch. All previous feature PRs have already been merged into it. Old feature branch names may still exist as historical refs, but they are not separate unfinished versions of the project.

`generated` intentionally remains separate because Kodi reads the automatically published M3U/XMLTV files from it.

## Automatic build

`.github/workflows/update-generated.yml` runs daily, on relevant changes, and manually through GitHub Actions. It has a 30-minute ceiling and only publishes after regression tests and generated-output checks pass.

A failed build therefore does not intentionally replace the previous known-good generated output.

## Xbox/PVR recovery

Changing an existing Kodi M3U/XMLTV source can leave Kodi's local PVR cache out of sync even when the remote files are valid. After replacing the source URLs, clear Kodi's PVR channel cache and EPG cache once before treating the feed as broken.

The PC helper `tools/kodi-pvr-healthcheck.cmd` can query the Xbox through Kodi JSON-RPC and report the Kodi/IPTV Simple/PVR state without deleting settings. See [`docs/KODI_SETUP.md`](docs/KODI_SETUP.md) for the exact recovery sequence.

## Stream validation

Stream health is deliberately separate from playlist generation. A single HTTP failure is not enough to delete a channel because IPTV/FAST streams can be geo-blocked, rate-limited, temporarily unavailable or require particular request behaviour.

`tools/validate_streams.py` is the local conservative checker and should be run from the same network as the Xbox when a cleanup is actually needed.

## Kodi UI / Sky-Q-style phase

The data layer is no longer the main project blocker. The next phase is making Kodi behave like a dedicated TV appliance rather than a generic media centre.

Priorities:

1. tune the installed Sky/Sky-Q-style skin so **TV / Guide / channels** dominate the home screen;
2. expose useful channel groups and favourites cleanly;
3. surface **BBC iPlayer content directly on the Kodi home screen** using the skin's custom menu/widget system instead of repeatedly opening Video add-ons;
4. create direct iPlayer entry points for useful sections such as featured/popular programmes, categories and films where the installed iPlayer WWW add-on exposes them;
5. add reliable ITVX / Channel 4 / My5 integrations only after iPlayer is behaving properly;
6. finish controller/remote navigation and visual polish last.

BBC iPlayer playback is already working on the Xbox. The remaining work is **navigation and widget integration**, not basic iPlayer setup.

## Project status

See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for the current handoff and [`docs/KODI_SETUP.md`](docs/KODI_SETUP.md) for Kodi/PVR configuration details.
