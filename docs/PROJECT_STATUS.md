# Project status / handoff

Current checkpoint for the Kodi-on-Xbox IPTV project.

## Repository state

`main` is the canonical development branch. All historical feature PRs are already merged. The `generated` branch remains separate intentionally because it is the automatically published output Kodi consumes.

The retired provider-by-provider EPG scraper chain has now been removed from `main`, including its catalog, channel-mapping, fallback, batching, split/merge helpers and their dedicated tests.

The production path is the fast prebuilt-feed pipeline only.

## Kodi endpoints

Normal setup:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u`
- XMLTV: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

UK-only alternative:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-uk.m3u`
- XMLTV: same shared guide

The PC remains a setup/maintenance workstation only.

## FAST services

The normal English build now appends maintained free FAST sources before guide curation:

- Samsung TV Plus GB
- Pluto TV GB
- Plex TV GB
- Roku Channel

Each source receives an extra Kodi group such as `FAST - Samsung TV Plus` while retaining its original genre group. Duplicate stream URLs are skipped.

Matching service-native XMLTV feeds from `i.mjh.nz` are included in `epg-feeds.txt`, so these channels can survive into `curated.m3u` when real programme rows are present.

## Historical verified checkpoint

Before FAST integration, the 2026-09-11 verified build contained 352 channels with programme data and 37,738 programme rows. That figure is now historical; use the current `guide-stats.json` and playlist-stat files on the `generated` branch for authoritative live figures.

## Kodi / Xbox UI phase

The backend is no longer the main blocker. The current goal is a coherent Sky-Q-style appliance experience.

Order of work:

1. confirm Kodi is using `curated.m3u` + `guide.xml.gz` after the latest generated build;
2. tune the installed Sky/Sky-Q-style skin so TV/Guide is the dominant home experience;
3. expose channel groups and favourites cleanly, including the FAST service groups;
4. surface BBC iPlayer content directly as home-screen widgets/menu targets;
5. add direct iPlayer entry points for useful sections such as Most Popular, Highlights, Categories, A-Z and Live where useful;
6. only then look at other legitimate catch-up services that work reliably on Xbox Kodi;
7. finish controller/remote behaviour and visual polish last.

BBC iPlayer playback is already working. The remaining iPlayer work is navigation/widget integration rather than authentication or basic playback.

## iPlayer widget strategy

The installed add-on is `plugin.video.iplayerwww`. Its current code exposes top-level modes for Live, A-Z, Categories, Most Popular, Highlights, Watching, Favourites and channel listings.

For the skin setup, prefer navigating to the desired iPlayer folder in Kodi and adding that folder to **Favourites**, then selecting that favourite as a skin widget or submenu target. This avoids hard-coding internal plugin query URLs and still lets the widget refresh from iPlayer dynamically.

Suggested first home rows:

- iPlayer — Most Popular
- iPlayer — Highlights
- iPlayer — Categories
- iPlayer — Live / Channels

The exact widget/menu clicks depend on the installed skin and should be configured on the Xbox from screenshots of its customization screen.

## Diagnostics if TV data looks wrong

Check in this order:

1. `last-update.txt` is current;
2. `guide-stats.json` reports downloaded sources and programme rows;
3. `curated-playlist-stats.json` reports non-zero kept entries;
4. `epg-coverage.txt` shows expected matches;
5. `epg-failures.txt` explains any failed FAST/EPG source;
6. fully restart Kodi;
7. only then clear/reload Kodi PVR/EPG data if necessary.

Do not reintroduce the retired multi-hour scraper merely because some channels remain unmatched.
