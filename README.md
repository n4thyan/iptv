# Net IPTV playlist pack

Built for the older Samsung **Net IPTV / netiptv.eu** app.

## Recommended four-list layout

| Slot | Purpose | URL |
|---|---|---|
| 1 | UK | `https://iptv-org.github.io/iptv/countries/uk.m3u` |
| 2 | Western Europe | `https://iptv-org.github.io/iptv/regions/wer.m3u` |
| 3 | English-language worldwide | `https://iptv-org.github.io/iptv/languages/eng.m3u` |
| 4 | Adult / call-in / participation extras | `https://raw.githubusercontent.com/n4thyan/iptv/main/netiptv-extras-adult-callin.m3u` |

## Adult / call-in extras

The custom list currently contains 32 entries, including Xpanded TV, Babestation24, VISIT-X TV, Miami TV variants, A3 Bikini, FashionTV Midnight Secrets and public AdultIPTV.net category feeds.

The ambiguous `AdultIPTV.net Teen` feed is intentionally not included.

The list does **not** contain leaked Xtream credentials, subscription usernames/passwords or private paid IPTV accounts.

## Samsung / Net IPTV setup

1. Open `https://netiptv.eu/home/upload`.
2. Enter the MAC / APP ID shown by Net IPTV on the Samsung TV.
3. Paste the four URLs above into List 1–4.
4. Click **Add ALL List**.
5. Re-open Net IPTV on the TV, or press `0` to request a playlist reload.
6. The adult streams should appear under the `07 Adult 18+` group and the participation channels under `06 Call-in & Participation`.

If the large English-language playlist makes the older Samsung app sluggish, replace List 3 with:

`https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8`

## EPG

The IPTV-org lists include `tvg-id` metadata that can be matched against XMLTV data. The custom list keeps known `tvg-id` values where available, but conventional programme-guide coverage is expected to be limited for many adult/call-in streams.

## Notes

Public IPTV streams are volatile. Individual streams can move, disappear, become geo-blocked, or stop working without warning. The next refinement pass can add more public sources, validate current reachability, deduplicate channels and improve EPG coverage.
