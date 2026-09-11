#!/usr/bin/env python3
"""Select alternate EPG sources for channels still missing programmes.

``build_epg_channels.py`` writes a ranked source manifest for every playlist
channel.  After the first grab, this script finds channels that produced no
programme records and emits another iptv-org/epg ``channels.xml`` using the next
ranked source.  Re-running with ``--candidate-index 2`` provides a second
fallback pass without inventing or fuzzy-matching guide data.
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def channels_with_programmes(path: Path) -> set[str]:
    result: set[str] = set()
    if not path.exists() or path.stat().st_size == 0:
        return result
    for _event, elem in ET.iterparse(path, events=("end",)):
        if elem.tag == "programme":
            channel = elem.attrib.get("channel", "").strip()
            if channel:
                result.add(channel)
        elem.clear()
    return result


def build_channel(target: str, source: dict[str, str]) -> ET.Element:
    attrs = {
        "site": str(source.get("site", "")),
        "site_id": str(source.get("site_id", "")),
        "lang": str(source.get("lang", "")),
        "xmltv_id": target,
    }
    channel = ET.Element("channel", attrs)
    channel.text = str(source.get("name", ""))
    return channel


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", default="output/epg-candidates.json")
    parser.add_argument("--guide", required=True)
    parser.add_argument("--candidate-index", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--stats", required=True)
    args = parser.parse_args()

    if args.candidate_index < 1:
        parser.error("--candidate-index must be at least 1; index 0 is the primary source")

    manifest = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    candidates = manifest.get("candidates", {})
    if not isinstance(candidates, dict):
        parser.error("candidate manifest has no candidates mapping")

    already_covered = channels_with_programmes(Path(args.guide))
    root = ET.Element("channels")
    requested = 0
    no_alternate = 0
    skipped_covered = 0

    for target in sorted(candidates):
        if target in already_covered:
            skipped_covered += 1
            continue
        ranked = candidates.get(target) or []
        if not isinstance(ranked, list) or len(ranked) <= args.candidate_index:
            no_alternate += 1
            continue
        source = ranked[args.candidate_index]
        if not isinstance(source, dict):
            no_alternate += 1
            continue
        if not source.get("site") or not source.get("site_id"):
            no_alternate += 1
            continue
        root.append(build_channel(target, source))
        requested += 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output, encoding="utf-8", xml_declaration=True)

    stats = {
        "candidate_index": args.candidate_index,
        "guide": args.guide,
        "channels_already_with_programmes": len(already_covered),
        "channels_skipped_already_covered": skipped_covered,
        "channels_without_this_alternate": no_alternate,
        "fallback_channels_requested": requested,
    }
    stats_path = Path(args.stats)
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
