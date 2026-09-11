#!/usr/bin/env python3
"""Summarize a generated XMLTV guide without loading the whole file in memory."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def collect_stats(path: Path) -> dict[str, int | str]:
    channel_ids: set[str] = set()
    programme_channels: set[str] = set()
    channel_elements = 0
    programmes = 0
    programmes_without_channel = 0

    for _event, elem in ET.iterparse(path, events=("end",)):
        if elem.tag == "channel":
            channel_elements += 1
            channel_id = elem.attrib.get("id", "").strip()
            if channel_id:
                channel_ids.add(channel_id)
            elem.clear()
        elif elem.tag == "programme":
            programmes += 1
            channel_id = elem.attrib.get("channel", "").strip()
            if channel_id:
                programme_channels.add(channel_id)
            else:
                programmes_without_channel += 1
            elem.clear()

    return {
        "guide": str(path),
        "guide_bytes": path.stat().st_size,
        "channel_elements": channel_elements,
        "unique_channel_ids": len(channel_ids),
        "programme_elements": programmes,
        "channels_with_programmes": len(programme_channels),
        "programmes_without_channel": programmes_without_channel,
        "programme_channels_missing_definition": len(programme_channels - channel_ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="XMLTV guide.xml path")
    parser.add_argument("--output", default="output/guide-stats.json")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    stats = collect_stats(input_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
