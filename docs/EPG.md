# EPG plan for Kodi

## Goal

Provide one programme guide for the cleaned English-language playlist used by Kodi on Xbox, without requiring a PC to stay online.

The generated files are intended to live on the repository's `generated` branch and be refreshed automatically by GitHub Actions.

Once the first build succeeds, Kodi can use these directly:

- M3U: `https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u`
- XMLTV EPG: `https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz`

The PC is therefore only needed for development/maintenance, not for normal Kodi playback.

## Why IPTV-org/epg is the primary EPG engine

The English playlist comes from IPTV-org and carries `tvg-id` values. The `iptv-org/epg` project uses the same IPTV-org channel identifiers as its `xmltv_id` values, so it is the best starting point for matching guide data to the playlist.

The build does not assume every channel has EPG coverage. It creates a coverage report showing which playlist IDs could and could not be matched to an available guide source.

## XMLTV/xmltv

`https://github.com/XMLTV/xmltv` is also useful, but it solves a slightly different layer of the problem. It is a mature toolkit for obtaining, converting, filtering and post-processing XMLTV listings.

For this project the current plan is:

1. use `iptv-org/epg` to obtain listings because its channel IDs align with the IPTV-org playlist,
2. use XMLTV-compatible output (`guide.xml` / `guide.xml.gz`) in Kodi,
3. bring in XMLTV/xmltv utilities later if we need more advanced merging, filtering, time correction, validation or post-processing.

This avoids adding a Perl/XMLTV toolchain before it is actually needed.

## Current generation pipeline

1. Download `https://iptv-org.github.io/iptv/languages/eng.m3u`.
2. Download IPTV-org channel metadata.
3. Remove channels marked `is_nsfw=true` by IPTV-org, with a small fallback adult-name filter for entries that lack useful metadata.
4. Preserve the remaining channel metadata, stream URLs and `tvg-id` values.
5. Scan the `iptv-org/epg` channel definitions for matching `xmltv_id` values.
6. Prefer an English-language EPG source when several sources exist for one channel ID.
7. Generate a custom `epg.channels.xml` containing only IDs needed by our playlist.
8. Run the IPTV-org EPG grabber for those channels.
9. Produce `guide.xml.gz` and a human-readable `epg-coverage.txt` report.
10. Publish the cleaned M3U and EPG to the `generated` branch.

## Kodi setup

After the generated files exist:

1. Open **Add-ons > My add-ons > PVR clients > IPTV Simple Client > Configure**.
2. Edit the main configuration.
3. Under **General**, set the M3U playlist URL to the generated `english.m3u` URL above.
4. Under **EPG**, set the XMLTV URL to the generated `guide.xml.gz` URL above.
5. Save, fully quit Kodi and reopen it.
6. Open **TV > Guide** and verify populated channels.

## Stream validation

Stream validation is intentionally separate from EPG generation. A stream must not be deleted merely because one probe fails: public IPTV streams can be temporarily offline, geo-blocked, rate-limited, or reject a probe method while still working in Kodi.

The later validator should keep state across runs and classify streams as:

- working,
- geo-blocked/access-restricted,
- temporarily failed,
- repeatedly failed / likely dead.

Only repeatedly confirmed dead streams should be removed automatically.
