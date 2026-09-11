#!/usr/bin/env python3
"""Filter an M3U to channels that have real programme rows in an XMLTV guide."""

from __future__ import annotations

import argparse
import gzip
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')


def parse_extinf(extinf: str) -> dict[str, str]:
    return dict(ATTR_RE.findall(extinf))


def read_stanza(lines: list[str], start: int) -> tuple[list[str] | None, int]:
    stanza = [lines[start].strip()]
    index = start + 1
    while index < len(lines):
        raw = lines[index].strip()
        if not raw:
            index += 1
            continue
        if raw.startswith("#EXTINF"):
            return None, index
        stanza.append(raw)
        index += 1
        if not raw.startswith("#"):
            return stanza, index
    return None, index


def programme_channel_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    opener = gzip.open if path.suffix.casefold() == ".gz" else open
    with opener(path, "rb") as handle:
        for _event, element in ET.iterparse(handle, events=("end",)):
            if element.tag.rsplit("}", 1)[-1] == "programme":
                channel_id = element.attrib.get("channel", "").strip()
                if channel_id:
                    ids.add(channel_id)
            element.clear()
    return ids


def filter_playlist_text(text: str, allowed_ids: set[str]) -> tuple[str, dict[str, int]]:
    lines = [line.rstrip("\r") for line in text.splitlines()]
    header = next((line.strip() for line in lines if line.strip().startswith("#EXTM3U")), "#EXTM3U")
    output_lines = [header]
    total = kept = malformed = missing_id = 0

    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line.startswith("#EXTINF"):
            index += 1
            continue

        total += 1
        stanza, next_index = read_stanza(lines, index)
        if stanza is None:
            malformed += 1
            index = next_index
            continue

        attrs = parse_extinf(stanza[0])
        tvg_id = attrs.get("tvg-id", "").strip()
        if not tvg_id:
            missing_id += 1
        elif tvg_id in allowed_ids:
            output_lines.extend(stanza)
            kept += 1

        index = next_index

    stats = {
        "entries_total": total,
        "entries_kept": kept,
        "entries_without_programme_data": total - kept,
        "entries_missing_tvg_id": missing_id,
        "malformed_entries_skipped": malformed,
        "programme_channel_ids_available": len(allowed_ids),
    }
    return "\n".join(output_lines) + "\n", stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", required=True)
    parser.add_argument("--guide", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--stats", required=True)
    args = parser.parse_args()

    playlist_path = Path(args.playlist).resolve()
    guide_path = Path(args.guide).resolve()
    output_path = Path(args.output).resolve()
    stats_path = Path(args.stats).resolve()

    allowed_ids = programme_channel_ids(guide_path)
    if not allowed_ids:
        raise SystemExit("guide contains no programme channel IDs")

    filtered, stats = filter_playlist_text(
        playlist_path.read_text(encoding="utf-8-sig"),
        allowed_ids,
    )
    if stats["entries_kept"] == 0:
        raise SystemExit("no playlist channels matched programme data")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(filtered, encoding="utf-8")
    stats_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
