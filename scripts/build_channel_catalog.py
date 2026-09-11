#!/usr/bin/env python3
"""Build a compact channel metadata catalog for EPG matching.

The playlist contains exact feed IDs such as ``BBCOne.uk@London`` while the
IPTV-org channel database stores metadata on the base channel ID
(``BBCOne.uk``).  This script joins those two views and preserves the playlist
name so later EPG matching can make conservative, explainable decisions.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
DEFAULT_CHANNELS_API = "https://iptv-org.github.io/api/channels.json"
DEFAULT_PLAYLIST = "output/english.m3u"


def load_text(source: str) -> str:
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(source, headers={"User-Agent": "Kodi-IPTV-Catalog/1.0"})
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.read().decode("utf-8-sig", errors="replace")
    return Path(source).read_text(encoding="utf-8-sig")


def base_id(tvg_id: str) -> str:
    return tvg_id.split("@", 1)[0].strip()


def playlist_entries(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("#EXTINF"):
            continue
        attrs = dict(ATTR_RE.findall(line))
        tvg_id = attrs.get("tvg-id", "").strip()
        if not tvg_id:
            continue
        name = line.rsplit(",", 1)[-1].strip() if "," in line else ""
        entries.setdefault(tvg_id, name)
    return entries


def load_database(source: str) -> dict[str, dict]:
    data = json.loads(load_text(source))
    result: dict[str, dict] = {}
    for item in data:
        channel_id = str(item.get("id", "")).strip()
        if channel_id:
            result[channel_id] = item
    return result


def clean_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", default=DEFAULT_PLAYLIST)
    parser.add_argument("--channels-api", default=DEFAULT_CHANNELS_API)
    parser.add_argument("--output", default="output/channel-catalog.json")
    args = parser.parse_args()

    playlist = playlist_entries(load_text(args.playlist))
    database = load_database(args.channels_api)

    catalog: dict[str, dict] = {}
    database_hits = 0
    for tvg_id, playlist_name in sorted(playlist.items()):
        base = base_id(tvg_id)
        item = database.get(base, {})
        if item:
            database_hits += 1
        name = str(item.get("name") or playlist_name).strip()
        aliases = clean_string_list(item.get("alt_names"))
        network = str(item.get("network") or "").strip()
        country = str(item.get("country") or "").strip()
        catalog[tvg_id] = {
            "base_id": base,
            "playlist_name": playlist_name,
            "name": name,
            "alt_names": aliases,
            "network": network,
            "country": country,
        }

    output = {
        "playlist": args.playlist,
        "playlist_tvg_ids": len(playlist),
        "database_records_matched": database_hits,
        "channels": catalog,
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: output[k] for k in ("playlist_tvg_ids", "database_records_matched")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
