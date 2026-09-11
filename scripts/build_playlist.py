#!/usr/bin/env python3
"""Build a conservative Kodi-ready playlist from IPTV-org's English M3U.

This script deliberately avoids aggressive stream pruning. A single failed probe is
not enough evidence that an IPTV stream is dead. For now it:

- downloads the English-language playlist
- removes adult/18+/XXX entries
- preserves the original EXTINF metadata and stream URLs
- writes the tvg-id set used by the EPG builder
- writes basic build statistics
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

DEFAULT_SOURCE = "https://iptv-org.github.io/iptv/languages/eng.m3u"
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


def fetch_text(source: str) -> str:
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"User-Agent": "Kodi-IPTV-Cleaner/1.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.read().decode("utf-8-sig", errors="replace")
    return Path(source).read_text(encoding="utf-8-sig")


def parse_entry(extinf: str, url: str) -> tuple[dict[str, str], str, str]:
    attrs = dict(ATTR_RE.findall(extinf))
    name = extinf.rsplit(",", 1)[-1].strip() if "," in extinf else ""
    return attrs, name, url.strip()


def is_adult(attrs: dict[str, str], name: str) -> bool:
    # Do not accidentally remove the unrelated Cartoon Network block "Adult Swim".
    lowered_name = name.casefold()
    if "adult swim" in lowered_name:
        return False

    group = attrs.get("group-title", "").casefold()
    haystack = f"{group} {lowered_name}"
    return any(term in haystack for term in EXPLICIT_ADULT_TERMS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", default="output/english.m3u")
    parser.add_argument("--ids", default="output/channel_ids.txt")
    parser.add_argument("--stats", default="output/playlist-stats.json")
    args = parser.parse_args()

    text = fetch_text(args.source)
    lines = [line.rstrip("\r") for line in text.splitlines()]

    output_lines = ["#EXTM3U"]
    tvg_ids: set[str] = set()
    total = kept = removed_adult = malformed = 0

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("#EXTINF"):
            i += 1
            continue

        total += 1
        if i + 1 >= len(lines):
            malformed += 1
            break

        url = lines[i + 1].strip()
        attrs, name, url = parse_entry(line, url)
        if not url or url.startswith("#"):
            malformed += 1
            i += 2
            continue

        if is_adult(attrs, name):
            removed_adult += 1
            i += 2
            continue

        output_lines.extend([line, url])
        kept += 1
        tvg_id = attrs.get("tvg-id", "").strip()
        if tvg_id:
            tvg_ids.add(tvg_id)

        i += 2

    output_path = Path(args.output)
    ids_path = Path(args.ids)
    stats_path = Path(args.stats)
    for path in (output_path, ids_path, stats_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    ids_path.write_text("\n".join(sorted(tvg_ids)) + "\n", encoding="utf-8")

    stats = {
        "source": args.source,
        "entries_total": total,
        "entries_kept": kept,
        "adult_entries_removed": removed_adult,
        "malformed_entries_skipped": malformed,
        "unique_tvg_ids": len(tvg_ids),
    }
    stats_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
