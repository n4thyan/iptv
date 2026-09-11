# IPTV / Kodi playlist project

Clean IPTV source list and maintenance notes for Nathan's Kodi setup.

## Current setup

The main working frontend is **Kodi on Xbox** using **PVR IPTV Simple Client**.

Current public playlist sources:

| Purpose | URL |
|---|---|
| UK | `https://iptv-org.github.io/iptv/countries/uk.m3u` |
| Western Europe | `https://iptv-org.github.io/iptv/regions/wer.m3u` |
| English-language worldwide | `https://iptv-org.github.io/iptv/languages/eng.m3u` |

The English-language worldwide list is currently the main source because it gives broad coverage and is already working in Kodi.

## Removed sources

The old custom adult/call-in playlist has been removed because the streams were not working reliably. It should not be re-added unless there is a validated reason to do so.

## EPG status

Kodi's EPG UI is working, but guide data still needs to be matched correctly to the playlist channel IDs. The previous direct UK XMLTV test did not populate the UK playlist consistently because the channel identifiers did not match.

The intended fix is to build a small maintenance pipeline that:

1. downloads the source playlist(s),
2. preserves `tvg-id`, channel name, logo and group metadata,
3. matches channels to compatible XMLTV/EPG data by ID,
4. validates streams without deleting them after a single transient failure,
5. removes confirmed dead streams and bad duplicates,
6. outputs a cleaned Kodi-ready M3U and XMLTV guide.

## Stream validation policy

Do not treat one failed request as proof that a channel is dead. IPTV streams can be temporarily unavailable, geo-blocked or reject certain probe methods while still playing in Kodi.

A cleaner should classify streams before removal, for example:

- working
- geo-blocked / access-restricted
- temporarily failed
- confirmed dead

Only confirmed dead streams should be removed automatically.

## Next priorities

- Get reliable UK EPG matching working.
- Add automated stream validation and deduplication.
- Generate a cleaner playlist for Kodi rather than manually editing thousands of channels.
- Preserve useful channel groups and make UK/favourite channels easy to reach.
- Keep the setup lightweight: no random Kodi builds or unnecessary repositories.

## Notes

Public IPTV streams are volatile. Individual streams can move, disappear, become geo-blocked or return later, so generated playlists should be refreshable rather than treated as permanent static data.
