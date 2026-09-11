# IPTV / Kodi playlist project

Clean IPTV source, EPG generation and maintenance tooling for a Kodi-on-Xbox setup.

## Main Kodi source

The base playlist is IPTV-org's English-language worldwide list:

`https://iptv-org.github.io/iptv/languages/eng.m3u`

The repository now builds its own cleaned copy from that source rather than requiring thousands of channels to be maintained manually.

When the automated EPG build has completed successfully, the Kodi-facing files are published from the `generated` branch:

- Playlist: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- EPG: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`
- EPG coverage report: `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-coverage.txt`
- Playlist build stats: `https://raw.githubusercontent.com/n4thyan/iptv/generated/playlist-stats.json`

The generated M3U also embeds the EPG URL in its `x-tvg-url` header for clients that support it.

## What the automatic build does

The GitHub Actions workflow:

1. downloads the current English IPTV-org playlist,
2. removes adult/NSFW entries using IPTV-org channel metadata plus a conservative fallback filter,
3. preserves `tvg-id`, logos, channel groups, stream URLs and Kodi/VLC stream directives,
4. scans IPTV-org's EPG definitions for matching channel IDs,
5. uses same-channel feed aliases when appropriate to improve coverage,
6. splits the large EPG job into small batches so the upstream Node grabber does not exhaust memory,
7. downloads programme data for two days,
8. merges the successful XMLTV fragments,
9. validates the generated M3U/XMLTV files,
10. publishes the finished files to the `generated` branch.

The workflow runs daily and can also be started manually.

## EPG coverage

The target is the **entire English playlist**, not just UK channels. IPTV-org's EPG tooling is the primary source because its `xmltv_id` identifiers align with the `tvg-id` values used by the IPTV-org playlist.

Not every public IPTV channel has real schedule data available. The build therefore produces `epg-coverage.txt` showing exact matches, safe same-channel aliases and channels for which no compatible EPG source is currently known. Missing guide data is not fabricated.

`XMLTV/xmltv` is also useful and is documented as a possible second-stage toolkit for filtering, merging or augmenting listings if we need to push coverage further.

See [`docs/EPG.md`](docs/EPG.md) for the architecture and Kodi setup notes.

## Adult channels

The old custom adult/call-in playlist has been removed because those streams were not working reliably. The generated English playlist also filters channels that IPTV-org marks as NSFW/adult.

## Dead-stream cleanup

Do **not** remove a stream after one failed HTTP request. IPTV streams can be temporarily unavailable, geo-blocked, rate-limited or require headers that a simplistic checker does not send.

`tools/validate_streams.py` provides a conservative local health check using `ffprobe`. It is intentionally designed to run from the same UK network as the Xbox rather than from GitHub's cloud runners, so geo-restricted streams are not falsely classified as dead.

It classifies streams as:

- working,
- access/geo restricted,
- temporarily failed,
- dead,
- untested Kodi web-scraper entries.

Ordinary failures need repeated failed validation runs before automatic removal. See [`docs/STREAM_VALIDATION.md`](docs/STREAM_VALIDATION.md).

## Other source references

| Purpose | URL |
|---|---|
| UK-only | `https://iptv-org.github.io/iptv/countries/uk.m3u` |
| Western Europe | `https://iptv-org.github.io/iptv/regions/wer.m3u` |
| English worldwide | `https://iptv-org.github.io/iptv/languages/eng.m3u` |

## Kodi

Kodi on Xbox uses **PVR IPTV Simple Client**. Once the generated branch is populated, the intended final configuration is simply:

- **M3U playlist URL** → generated `english.m3u`
- **XMLTV URL** → generated `guide.xml.gz`

After that Kodi can handle the normal TV guide, channel groups, favourites and the eventual Sky-style skin without requiring a PC to remain switched on.

## Project philosophy

Keep the setup lightweight and understandable: stock Kodi, official/known components, direct playlist/EPG data and small purpose-built tools. No giant third-party Kodi builds or mystery repository bundles.
