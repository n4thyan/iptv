# Project status / handoff

Current checkpoint for the Kodi-on-Xbox IPTV project.

## Repository state

`main` is the canonical development branch. All historical feature PRs are already merged. The `generated` branch remains separate intentionally because it is the automatically published output Kodi consumes.

The retired provider-by-provider EPG scraper chain has been removed from `main`. The production path is the fast prebuilt-feed pipeline only.

## Kodi endpoints

Normal setup:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u`
- XMLTV (recommended Xbox rolling guide): `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`
- XMLTV (full/heavier guide): `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-full.xml.gz`

UK-only alternative:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-uk.m3u`
- XMLTV: same recommended rolling guide

The PC remains a setup/maintenance workstation only.

## FAST services

The normal English build appends maintained free FAST sources before guide curation:

- Samsung TV Plus GB
- Pluto TV GB
- Plex TV GB
- Roku Channel

Each source receives an extra Kodi group such as `FAST - Samsung TV Plus` while retaining its original genre group. Duplicate stream URLs are skipped.

Matching service-native XMLTV feeds from `i.mjh.nz` are included in `epg-feeds.txt`, so these channels survive into `curated.m3u` when real programme rows are present.

## Current verified build — 2026-09-14

The full generated data remains:

- requested playlist IDs: 3,978
- curated channels with programme data: 1,300
- full programme rows: 81,342
- EPG sources configured/downloaded: 23 / 23
- EPG source failures: 0
- curated playlist entries kept: 1,300

FAST exact-ID contributions include:

- Samsung TV Plus GB: 267 channels / 2,559 programme rows
- Pluto TV GB: 118 channels / 2,844 programme rows
- Plex TV GB: 364 channels / 15,706 programme rows
- Roku: 245 channels / 21,731 programme rows

For Xbox, `guide.xml.gz` is now generated from a rolling window around the current time. The latest verified rolling build keeps all 1,300 channels but reduces programme rows from 81,342 to 43,761 (46.2% fewer). The untrimmed guide remains available as `guide-full.xml.gz`.

Both the build and generated-file verification workflows pass with the rolling guide.

## Current Xbox state

The new curated M3U and XMLTV URLs have been entered into the Xbox's main IPTV Simple configuration. The old separate UK configuration was disabled/removed from the active setup.

Observed Xbox add-on versions/settings:

- IPTV Simple Client: **21.10.1**
- InputStream Adaptive: **21.5.9**
- InputStream FFmpeg Direct: **21.3.7**
- RTMP Input: **21.1.2**
- EPG URL points to `generated/guide.xml.gz`
- EPG time shift: `0.0 hours`
- XMLTV local caching: enabled
- channel logos: `Prefer M3U`
- timeshift: disabled
- TV groups: all groups

The same `curated.m3u` loads and plays correctly in IPTVnator on the PC (1,300 channels), so the remote playlist is demonstrably usable outside Kodi.

Kodi on Xbox is currently hanging at **PVR manager is starting up** after the source migration. Given the valid generated files, successful external playback, and enabled Kodi local caches, treat this first as a **local Kodi/PVR cache/state migration problem**, not a broken playlist.

## Xbox recovery path

IPTV Simple's own documentation says that after changing channel-source configuration Kodi's full PVR cache should be cleared, and after changing EPG configuration the EPG cache should be cleared.

Next recovery sequence on Xbox:

1. **Settings → PVR & Live TV → General → Clear cache**
2. **Settings → PVR & Live TV → Guide → Clear cache**
3. fully quit Kodi from the Xbox dashboard;
4. reopen Kodi and allow PVR Manager to rebuild from `curated.m3u` + the rolling `guide.xml.gz`.

Do this once for the source migration, not on every launch.

New PC helpers on `main`:

- `tools/kodi-url-helper.cmd` — now auto-detects/retains the last working Kodi IP locally and offers both rolling/full EPG URLs;
- `tools/kodi-pvr-healthcheck.cmd` — reports Kodi version, IPTV Simple version and PVR availability over JSON-RPC;
- `tools/kodi-pvr-restart.cmd` — safely toggles IPTV Simple off/on without deleting its configuration.

If the cache reset still leaves PVR unavailable, run the healthcheck/restart helper and inspect Kodi's local log/PVR state before changing the feed again.

## Kodi / Xbox UI phase

Do not spend time tuning the Sky-Q-style skin until PVR startup is stable.

Once Live TV/Guide is loading normally, continue in this order:

1. tune the installed Sky/Sky-Q-style skin so TV/Guide is the dominant home experience;
2. expose channel groups and favourites cleanly, including FAST service groups;
3. surface BBC iPlayer content directly as home-screen widgets/menu targets;
4. add direct iPlayer entry points for Most Popular, Highlights, Categories, A-Z and Live;
5. only then look at other legitimate catch-up services that work reliably on Xbox Kodi;
6. finish controller/remote behaviour and visual polish last.

BBC iPlayer playback is already working. The remaining iPlayer work is navigation/widget integration rather than authentication or basic playback.

## iPlayer widget strategy

The installed add-on is `plugin.video.iplayerwww`. Its current code exposes top-level modes for Live, A-Z, Categories, Most Popular, Highlights, Watching, Favourites and channel listings.

For the skin setup, prefer navigating to the desired iPlayer folder in Kodi and adding that folder to **Favourites**, then selecting that favourite as a skin widget or submenu target. This avoids hard-coding internal plugin query URLs and still lets the widget refresh dynamically.

Suggested first home rows:

- iPlayer — Most Popular
- iPlayer — Highlights
- iPlayer — Categories
- iPlayer — Live / Channels

## Diagnostics if TV data looks wrong

Check in this order:

1. generated outputs and workflows are healthy;
2. test `curated.m3u` in another player if needed;
3. run `tools/kodi-pvr-healthcheck.cmd`;
4. after a source migration, clear Kodi's PVR and EPG caches once;
5. restart IPTV Simple with `tools/kodi-pvr-restart.cmd` if PVR remains unavailable;
6. inspect Kodi logs/local PVR state before changing the feed pipeline again.

Do not reintroduce the retired multi-hour scraper merely because some channels remain unmatched.
