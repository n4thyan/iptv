# Kodi on Xbox — current IPTV setup

These steps use the generated curated playlist/EPG, not raw upstream URLs.

## 1. Recommended sources

For normal use:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u`
- XMLTV: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

For a UK-only installation:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-uk.m3u`
- XMLTV: keep the same guide URL

The broader `english.m3u` and `uk.m3u` outputs still exist, but they intentionally contain many channels with no programme data. Use them only when browsing the full source list is more important than a clean guide.

## 2. Fastest Xbox entry method

You do not need to type long GitHub URLs with the Xbox controller.

Enable:

**Settings → Services → Control → Allow remote control via HTTP**

Then, with the target text field open on Kodi, run `tools\kodi-url-helper.cmd` on the PC. Its first choice is the curated English playlist, followed by the shared EPG and curated UK playlist.

This uses Kodi JSON-RPC only for text entry. The PC is not a permanent host and can be switched off afterwards.

## 3. IPTV Simple Client

Open:

**Add-ons → My add-ons → PVR clients → IPTV Simple Client → Configure**

Under **General**:

- Location: **Remote path (Internet address)**
- M3U playlist URL: curated English or curated UK URL above

Under **EPG**:

- Location: **Remote path (Internet address)**
- XMLTV URL: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

Save the configuration.

## 4. Reload Kodi

Fully quit Kodi from the Xbox dashboard, then reopen it. Let PVR Manager finish importing before judging the guide.

Open:

**TV → Guide**

The generated guide rewrites programme/channel IDs to the exact playlist `tvg-id` values, so Kodi can attach listings without manual per-channel mapping.

## 5. What the EPG matcher actually does

Production guide generation uses current prebuilt XMLTV feeds. It accepts exact IDs first, then only explicit conservative compatibility cases such as known punctuation/quality differences, known provider dataset suffixes and explicit regional aliases. Ambiguous matches are rejected.

This is deliberately different from the retired slow provider-by-provider scraper. The current production build is designed to finish quickly and publish only real matched programme rows.

## 6. Diagnostics

If the guide is empty or stale, check:

- `https://raw.githubusercontent.com/n4thyan/iptv/generated/last-update.txt`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-stats.json`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-playlist-stats.json`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-coverage.txt`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-failures.txt`

If those look current and healthy, fully restart Kodi. Only then clear PVR/EPG data and let IPTV Simple import again if necessary.

## 7. Stream failures

A blank/failed stream is separate from EPG health. Public IPTV streams can be geo-restricted, temporarily unavailable or require request headers. Do not remove a stream because one probe fails.

Use the conservative local validator in `tools/validate_streams.py` when a proper cleanup pass is wanted.

## 8. Kodi presentation / catch-up phase

The data layer is now separate from the UI layer. Current Kodi-side work is:

1. tune the installed Sky/Sky-Q-style skin and guide layout;
2. arrange channel numbering, groups and favourites;
3. expose BBC iPlayer inside the main TV / Videos / Movies navigation using the skin's custom menu/widget features where practical;
4. add other legitimate catch-up services only where they work reliably on Xbox Kodi;
5. map controller/remote actions so normal viewing feels appliance-like.

BBC iPlayer playback already works; the remaining job is integrating it into the main navigation rather than treating it as an isolated add-on.

## 9. PC maintenance / backup

For actual files such as skin config, keymaps, artwork or backups, use the temporary SMB helper documented in `PC_TO_KODI.md`.

The PC remains optional for setup and maintenance only. Normal live TV, EPG refreshes and iPlayer playback do not require it to remain online.
