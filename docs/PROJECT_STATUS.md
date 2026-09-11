# Project status / handoff

This file is the quick checkpoint for the Kodi-on-Xbox IPTV project.

## Data pipeline: complete

The repository now owns the normal Kodi data flow instead of pointing Kodi directly at raw upstream files.

Final public endpoints after a successful generation run:

- Full English playlist: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- UK-only playlist: `https://raw.githubusercontent.com/n4thyan/iptv/generated/uk.m3u`
- Shared XMLTV guide: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`
- Generation timestamp: `https://raw.githubusercontent.com/n4thyan/iptv/generated/last-update.txt`
- Guide stats: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-stats.json`
- EPG coverage: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-coverage.txt`
- EPG retry summary: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-chunk-summary.txt`
- Isolated EPG failures: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-failures.txt`

The full English playlist is the recommended Xbox source. It preserves IPTV-org's normal categories and automatically adds a `UK` group for channels also present in IPTV-org's UK country feed. This avoids creating a duplicate second PVR configuration merely to get a UK group.

## Automated maintenance: complete

GitHub Actions now:

1. fetches fresh upstream English and UK playlists;
2. filters IPTV-org NSFW/adult channels plus a conservative fallback filter;
3. preserves channel IDs, logos, groups and Kodi/VLC stream directives;
4. adds the generated `UK` group to matching English-playlist channels;
5. maps playlist IDs to IPTV-org EPG definitions using exact IDs and safe same-channel aliases;
6. splits the guide into memory-safe batches;
7. retries failed batches one channel at a time;
8. merges all successful XMLTV fragments;
9. validates playlists and real programme records;
10. publishes only after validation succeeds;
11. independently reopens and verifies the published generated branch.

A failed run therefore leaves the previous known-good `generated` branch in place.

## Stream health: complete as a maintenance tool

`tools/validate_streams.py` can be run from the same UK network as the Xbox with `ffprobe`. It deliberately does not run as a destructive cloud cleanup because region restrictions and temporary upstream faults can make good streams look dead from GitHub runners.

A stream is only removed from the validator's cleaned output after repeated consecutive failures. Working, access-restricted and deliberately untestable Kodi scraper entries reset the failure streak.

See `docs/STREAM_VALIDATION.md`.

## Xbox setup when returning

Use one IPTV Simple Client configuration:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- XMLTV: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

Fully quit Kodi from the Xbox dashboard and reopen it. Let PVR Manager finish importing. In **TV > Guide**, use the group selector to check for the generated **UK** group.

Do not add the generated UK-only playlist as a second configuration unless duplicate UK channels in **All channels** are actually desired. If a UK-only installation is preferred instead, replace the main M3U URL with the generated `uk.m3u` URL.

## Kodi-side work still intentionally separate

These are presentation/user-preference jobs rather than missing pieces of the playlist/EPG generator:

- choose personal favourite channels;
- optionally reorder/hide channels in Kodi;
- tune logos/artwork if individual sources look poor;
- configure the One For All remote/controller mapping;
- choose/tune a Sky+/Sky-Q-style skin/guide layout;
- add radio sources;
- add legitimate catch-up integrations such as BBC/iPlayer where reliable on Xbox Kodi.

They should be done after the generated playlist/guide has been proven on the Xbox so UI work is not confused with data-source problems.

## If something looks wrong

Check in this order:

1. `last-update.txt` is current;
2. `guide-stats.json` contains channels and programme records;
3. `playlist-stats.json` reports `extra_groups.UK.entries_tagged` greater than zero;
4. `epg-chunk-summary.txt` and `epg-failures.txt` explain any upstream guide failures;
5. fully restart Kodi;
6. only then clear/reload Kodi PVR/EPG data if necessary.

Do not replace the generated URLs with raw upstream URLs just because one channel or one guide row is temporarily unavailable.
