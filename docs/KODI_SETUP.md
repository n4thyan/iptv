# Kodi on Xbox — current IPTV setup

These steps use the generated curated playlist/EPG, not raw upstream URLs.

## 1. Recommended sources

Normal use:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u`
- XMLTV (Xbox-optimised rolling guide): `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`
- XMLTV (full/heavier archive): `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-full.xml.gz`

UK-only installation:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-uk.m3u`
- XMLTV: keep the same recommended guide URL

The normal curated playlist includes matching-guide FAST channels from Samsung TV Plus GB, Pluto TV GB, Plex TV GB and Roku. They appear in additional groups such as `FAST - Samsung TV Plus` while retaining their genre groups.

The default `guide.xml.gz` is intentionally Xbox-friendly: it keeps all programme-backed channels but only a rolling window around the current time. The full guide is preserved separately as `guide-full.xml.gz` for desktop/testing use.

## 2. Fastest Xbox entry method

Enable:

**Settings → Services → Control → Allow remote control via HTTP**

Then, with the target text field open on Kodi, run `tools\kodi-url-helper.cmd` on the PC. The helper now remembers the last working Kodi IP locally and can auto-detect Kodi from devices already visible on the LAN. The local state file is gitignored and does not store the HTTP password.

The PC is only being used for setup/maintenance and can be switched off afterwards.

## 3. IPTV Simple Client

Open:

**Add-ons → My add-ons → PVR clients → IPTV Simple Client → Configure**

Under **General**:

- Location: **Remote path (Internet address)**
- M3U playlist URL: curated English or curated UK URL above
- Timeshift: leave disabled during initial setup

Under **EPG**:

- Location: **Remote path (Internet address)**
- XMLTV URL: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`
- EPG time shift: `0.0 hours`

Under **Channel Logos**:

- `Prefer M3U` is suitable for this playlist

Save the add-on configuration.

## 4. Important: clear Kodi's old PVR cache after changing sources

When replacing an existing M3U or XMLTV source, a restart alone is not always enough. IPTV Simple's own documentation requires clearing Kodi's cached PVR data for channel-source changes and the EPG cache for guide changes.

After changing this project's M3U/XMLTV URLs once, do:

1. **Settings → PVR & Live TV → General → Clear cache**
2. **Settings → PVR & Live TV → Guide → Clear cache**
3. fully quit Kodi from the Xbox dashboard;
4. reopen Kodi and let PVR Manager rebuild from the new files.

This is especially important when **Cache M3U at local storage** or **Cache XMLTV at local storage** is enabled, or when the Xbox was previously using a different playlist/configuration.

Do not repeatedly clear the cache during normal use. It is a migration/recovery step after changing the source configuration.

## 5. Xbox/PVR healthcheck from the PC

Run:

`tools\kodi-pvr-healthcheck.cmd`

It queries the Xbox over the Kodi HTTP/JSON-RPC connection and reports:

- Kodi version;
- IPTV Simple version and enabled state;
- whether Kodi currently reports PVR as available/scanning.

It does not delete settings or cache data.

If we need to restart only the IPTV Simple add-on without deleting its configuration, run from PowerShell:

`powershell -ExecutionPolicy Bypass -File .\tools\kodi-pvr-healthcheck.ps1 -RestartPvrClient`

If PVR still reports unavailable after the add-on restart, perform the two Kodi cache-clear steps above. That distinguishes a local Kodi/PVR state problem from a feed problem.

## 6. Guide and FAST groups

Open **TV → Guide**.

The curated build keeps only channels with real programme coverage. The guide builder rejects ambiguous mappings rather than guessing.

Use Kodi's channel-group selector to access groups such as:

- UK
- FAST - Samsung TV Plus
- FAST - Pluto TV
- FAST - Plex TV
- FAST - Roku Channel

Exact visible groups depend on which entries survive the current EPG curation pass.

## 7. BBC iPlayer on the home screen

BBC iPlayer WWW is already installed and working. The goal is to make its content appear directly on the Kodi home screen instead of repeatedly entering **Video add-ons → iPlayer WWW**.

The safest skin-independent method is:

1. open **iPlayer WWW**;
2. navigate to a useful folder such as **Most Popular**, **Highlights**, **Categories**, **A-Z** or **Live**;
3. open the context menu on that folder and choose **Add to favourites**;
4. open the installed skin's **Home menu / Widgets / Customize home menu** settings;
5. create an iPlayer submenu or widget and point it at the favourite you just created;
6. repeat for the rows you actually want.

This makes the home widget query iPlayer dynamically while avoiding fragile hard-coded plugin URLs.

A good first layout is:

- TV / Guide
- iPlayer — Most Popular
- iPlayer — Highlights
- iPlayer — Categories
- iPlayer — Live

The iPlayer WWW add-on currently exposes Live, A-Z, Categories, Most Popular, Highlights, Watching, Favourites and channel listings internally, so those are the useful surfaces to build around.

## 8. Sky-Q-style presentation phase

The remaining work after PVR is stable is mostly visual and navigational:

1. make **TV / Guide** the dominant home destination;
2. reduce generic Kodi clutter;
3. add clean iPlayer rows/widgets;
4. expose useful channel groups/favourites;
5. tune artwork, spacing, colours and guide density toward Sky Q;
6. finish Xbox controller/remote behaviour last.

The exact menu names differ by skin, so configure from screenshots of the skin's customization screen rather than guessing option names.

## 9. Feed diagnostics

If the guide is empty or stale, check:

- `https://raw.githubusercontent.com/n4thyan/iptv/generated/last-update.txt`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-stats.json`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/xbox-guide-stats.json`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-playlist-stats.json`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-coverage.txt`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-failures.txt`

If the generated files validate and the same M3U/EPG works in another player but Kodi remains on **PVR manager is starting up**, treat it as a local Kodi/PVR state problem first: run the PC healthcheck, then clear Kodi's PVR and EPG caches once.

## 10. Stream failures

A stream failure is separate from PVR/EPG health. Public IPTV/FAST streams can be geo-restricted, temporarily unavailable, rate-limited or dependent on request behaviour.

Use `tools/validate_streams.py` for a deliberate cleanup pass rather than deleting a channel after one failed probe.

## 11. PC maintenance / backup

For skin config, keymaps, artwork or backups, use the temporary SMB helper documented in `PC_TO_KODI.md`.

The PC remains optional for setup and maintenance only. Normal live TV, guide refreshes and iPlayer playback do not require it to remain online.
