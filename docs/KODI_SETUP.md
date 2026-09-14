# Kodi on Xbox — current IPTV setup

These steps use the generated curated playlist/EPG, not raw upstream URLs.

## 1. Recommended sources

Normal use:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated.m3u`
- XMLTV: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

UK-only installation:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-uk.m3u`
- XMLTV: keep the same guide URL

The normal curated playlist now includes matching-guide FAST channels from Samsung TV Plus GB, Pluto TV GB, Plex TV GB and Roku. They appear in additional groups such as `FAST - Samsung TV Plus` while retaining their genre groups.

## 2. Fastest Xbox entry method

Enable:

**Settings → Services → Control → Allow remote control via HTTP**

Then, with the target text field open on Kodi, run `tools\kodi-url-helper.cmd` on the PC. The PC is only being used to enter long text and can be switched off afterwards.

## 3. IPTV Simple Client

Open:

**Add-ons → My add-ons → PVR clients → IPTV Simple Client → Configure**

Under **General**:

- Location: **Remote path (Internet address)**
- M3U playlist URL: curated English or curated UK URL above

Under **EPG**:

- Location: **Remote path (Internet address)**
- XMLTV URL: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

Save, fully quit Kodi from the Xbox dashboard, reopen it, and let PVR Manager finish importing.

## 4. Guide and FAST groups

Open **TV → Guide**.

The main curated build now has substantially more programme-backed channels because the FAST sources use matching service-native XMLTV IDs. The guide builder still rejects ambiguous mappings rather than guessing.

Use Kodi's channel-group selector to access groups such as:

- UK
- FAST - Samsung TV Plus
- FAST - Pluto TV
- FAST - Plex TV
- FAST - Roku Channel

Exact visible groups depend on which entries survive the current EPG curation pass.

## 5. BBC iPlayer on the home screen

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

## 6. Sky-Q-style presentation phase

The data backend is now stable enough that the remaining work is mostly visual and navigational:

1. make **TV / Guide** the dominant home destination;
2. reduce generic Kodi clutter;
3. add clean iPlayer rows/widgets;
4. expose useful channel groups/favourites;
5. tune artwork, spacing, colours and guide density toward Sky Q;
6. finish Xbox controller/remote behaviour last.

The exact menu names differ by skin, so the next practical step is to configure from screenshots of the skin's customization screen rather than guessing option names.

## 7. Diagnostics

If the guide is empty or stale, check:

- `https://raw.githubusercontent.com/n4thyan/iptv/generated/last-update.txt`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide-stats.json`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/curated-playlist-stats.json`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-coverage.txt`
- `https://raw.githubusercontent.com/n4thyan/iptv/generated/epg-failures.txt`

If those are healthy, fully restart Kodi before clearing PVR/EPG data.

## 8. Stream failures

A stream failure is separate from EPG health. Public IPTV/FAST streams can be geo-restricted, temporarily unavailable, rate-limited or dependent on request behaviour.

Use `tools/validate_streams.py` for a deliberate cleanup pass rather than deleting a channel after one failed probe.

## 9. PC maintenance / backup

For skin config, keymaps, artwork or backups, use the temporary SMB helper documented in `PC_TO_KODI.md`.

The PC remains optional for setup and maintenance only. Normal live TV, guide refreshes and iPlayer playback do not require it to remain online.
