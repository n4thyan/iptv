# Kodi on Xbox — final IPTV setup

These steps are for the finished generated playlist/EPG, not the raw upstream URLs.

## 1. Open IPTV Simple Client

In Kodi:

**Add-ons → My add-ons → PVR clients → IPTV Simple Client → Configure**

Edit the main enabled configuration.

## 2. Playlist

Under **General**:

- Location: **Remote path (Internet address)**
- M3U playlist URL:

`https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`

## 3. EPG

Under **EPG**:

- Location: **Remote path (Internet address)**
- XMLTV URL:

`https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

Save the configuration.

## 4. Reload Kodi

Fully quit Kodi from the Xbox dashboard, then reopen it. Allow PVR Manager time to import the playlist and EPG.

Open:

**TV → Guide**

The playlist and XMLTV guide use the same IPTV-org channel IDs, so matching should happen by `tvg-id` rather than by fuzzy channel names.

## 5. If the guide looks stale

Do not immediately edit the URLs. First try a full Kodi restart. If necessary, clear PVR/EPG data from Kodi's PVR settings and let IPTV Simple repopulate it.

## Later UI work

Once this data layer is stable, the next Kodi-side jobs are:

1. UK and favourite channel groups,
2. sensible channel ordering,
3. logos/artwork cleanup,
4. remote/controller key mapping,
5. Sky+/Sky-Q-style skin/guide layout,
6. catch-up/live-TV integrations where they can be added cleanly.
