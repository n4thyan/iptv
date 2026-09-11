#!/usr/bin/env python3
"""Build a conservative Kodi-ready playlist from IPTV-org's English M3U.

Current behaviour:
- downloads the English-language playlist
- removes adult/NSFW channels using IPTV-org's own channel database
- applies a small name/group fallback for entries without useful metadata
- preserves each channel's EXTINF line, Kodi/VLC option directives and stream URL
- embeds the generated XMLTV URL in the M3U header for Kodi IPTV Simple Client
- writes the tvg-id set used by the EPG builder
- writes build statistics

This deliberately does NOT delete a stream merely because a single network probe
fails. Stream validation is kept separate so transient outages/geo-blocks do not
silently destroy the playlist.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

DEFAULT_SOURCE = "https://iptv-org.github.io/iptv/languages/eng.m3u"
DEFAULT_CHANNELS_API = "https://iptv-org.github.io/api/channels.json"
DEFAULT_EPG_URL = "https://raw.githubusercontent.com/n4thyan/iptv/generated/guide.xml.gz"
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')

EXPLICIT_ADULT_TERMS = {
    "adult",
    "xxx",
    "18+",
    "porn",
    "porno",
    "erotic",
    "sex tv",
    "sex channel",
    "babestation",
    "xpanded",
    "playboy",
    "redlight",
    "visit-x",
}


def fetch_bytes(source: str) -> bytes:
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"User-Agent": "Kodi-IPTV-Cleaner/1.2"})
        with urllib.request.urlopen(req, timeout=90) as response:
            return response.read()
    return Path(source).read_bytes()


def fetch_text(source: str) -> str:
    return fetch_bytes(source).decode("utf-8-sig", errors="replace")


def load_nsfw_ids(source: str) -> set[str]:
    try:
        data = json.loads(fetch_bytes(source).decode("utf-8"))
    except Exception as exc:  # fallback filter still works if API is unavailable
        print(f"warning: could not load IPTV-org channel metadata: {exc}")
        return set()

    return {
        str(channel.get("id", "")).strip()
        for channel in data
        if channel.get("is_nsfw") is True and channel.get("id")
    }


def parse_extinf(extinf: str) -> tuple[dict[str, str], str]:
    attrs = dict(ATTR_RE.findall(extinf))
    name = extinf.rsplit(",", 1)[-1].strip() if "," in extinf else ""
    return attrs, name


def base_channel_id(tvg_id: str) -> str:
    # IPTV-org feed IDs can look like Channel.country@FeedVariant. The NSFW flag
    # belongs to the base channel record before the @ suffix.
    return tvg_id.split("@", 1)[0].strip()


def adult_by_fallback(attrs: dict[str, str], name: str) -> bool:
    # Cartoon Network's Adult Swim block is not an adult/NSFW channel.
    lowered_name = name.casefold()
    if "adult swim" in lowered_name:
        return False

    group = attrs.get("group-title", "").casefold()
    haystack = f"{group} {lowered_name}"
    return any(term in haystack for term in EXPLICIT_ADULT_TERMS)


def read_stanza(lines: list[str], start: int) -> tuple[list[str] | None, int]:
    """Return one EXTINF stanza and the next input index.

    IPTV-org entries can contain lines such as #EXTVLCOPT, #KODIPROP or #WEBPROP
    between #EXTINF and the actual stream URL, so the URL is not necessarily the
    immediately following line.
    """

    stanza = [lines[start].strip()]
    i = start + 1
    while i < len(lines):
        raw = lines[i].strip()
        if not raw:
            i += 1
            continue
        if raw.startswith("#EXTINF"):
            # We reached the next channel before finding a URL.
            return None, i
        stanza.append(raw)
        i += 1
        if not raw.startswith("#"):
            return stanza, i
    return None, i


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--channels-api", default=DEFAULT_CHANNELS_API)
    parser.add_argument("--epg-url", default=DEFAULT_EPG_URL)
    parser.add_argument("--output", default="output/english.m3u")
    parser.add_argument("--ids", default="output/channel_ids.txt")
    parser.add_argument("--stats", default="output/playlist-stats.json")
    args = parser.parse_args()

    nsfw_ids = load_nsfw_ids(args.channels_api)
    text = fetch_text(args.source)
    lines = [line.rstrip("\r") for line in text.splitlines()]

    output_lines = [f'#EXTM3U x-tvg-url="{args.epg_url}"']
    tvg_ids: set[str] = set()
    total = kept = removed_adult = malformed = option_lines_preserved = 0
    removed_by_database = removed_by_fallback = 0

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("#EXTINF"):
            i += 1
            continue

        total += 1
        stanza, next_i = read_stanza(lines, i)
        if stanza is None:
            malformed += 1
            i = next_i
            continue

        extinf = stanza[0]
        attrs, name = parse_extinf(extinf)
        tvg_id = attrs.get("tvg-id", "").strip()
        database_match = bool(tvg_id and base_channel_id(tvg_id) in nsfw_ids)
        fallback_match = adult_by_fallback(attrs, name)

        if database_match or fallback_match:
            removed_adult += 1
            if database_match:
                removed_by_database += 1
            elif fallback_match:
                removed_by_fallback += 1
            i = next_i
            continue

        output_lines.extend(stanza)
        option_lines_preserved += sum(1 for item in stanza[1:-1] if item.startswith("#"))
        kept += 1
        if tvg_id:
            tvg_ids.add(tvg_id)

        i = next_i

    output_path = Path(args.output)
    ids_path = Path(args.ids)
    stats_path = Path(args.stats)
    for path in (output_path, ids_path, stats_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    ids_path.write_text("\n".join(sorted(tvg_ids)) + "\n", encoding="utf-8")

    stats = {
        "source": args.source,
        "epg_url_embedded": args.epg_url,
        "entries_total": total,
        "entries_kept": kept,
        "adult_entries_removed": removed_adult,
        "adult_removed_by_iptv_org_database": removed_by_database,
        "adult_removed_by_fallback_filter": removed_by_fallback,
        "malformed_entries_skipped": malformed,
        "option_directive_lines_preserved": option_lines_preserved,
        "unique_tvg_ids": len(tvg_ids),
        "iptv_org_nsfw_ids_loaded": len(nsfw_ids),
    }
    stats_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
