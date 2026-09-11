#!/usr/bin/env python3
"""Build a custom iptv-org/epg channels file for the English playlist.

The IPTV-org playlist uses tvg-id values such as BBCOne.uk. The iptv-org/epg
repository uses the same identifiers as xmltv_id values in its *.channels.xml
files. This script finds one usable EPG source for as many playlist IDs as
possible and emits a custom channels XML file for the grabber.
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def load_ids(path: Path) -> set[str]:
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def candidate_score(channel: ET.Element, source_path: Path) -> tuple[int, str, str]:
    # Prefer English listings where available, then choose deterministically.
    lang = channel.attrib.get("lang", "").casefold()
    lang_score = 0 if lang == "en" else 1
    site = channel.attrib.get("site", "")
    return (lang_score, site.casefold(), str(source_path).casefold())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", default="output/channel_ids.txt")
    parser.add_argument("--sites-root", required=True)
    parser.add_argument("--output", default="output/epg.channels.xml")
    parser.add_argument("--coverage", default="output/epg-coverage.txt")
    args = parser.parse_args()

    wanted = load_ids(Path(args.ids))
    sites_root = Path(args.sites_root)
    candidates: dict[str, list[tuple[tuple[int, str, str], ET.Element, Path]]] = defaultdict(list)
    parse_errors: list[str] = []

    for path in sorted(sites_root.rglob("*.channels.xml")):
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            parse_errors.append(f"{path}: {exc}")
            continue

        for channel in root.findall("channel"):
            xmltv_id = channel.attrib.get("xmltv_id", "").strip()
            if xmltv_id not in wanted:
                continue
            cloned = ET.Element("channel", dict(channel.attrib))
            cloned.text = channel.text or ""
            candidates[xmltv_id].append((candidate_score(channel, path), cloned, path))

    selected: dict[str, tuple[ET.Element, Path]] = {}
    for xmltv_id, items in candidates.items():
        items.sort(key=lambda item: item[0])
        _, channel, path = items[0]
        selected[xmltv_id] = (channel, path)

    root = ET.Element("channels")
    for xmltv_id in sorted(selected):
        root.append(selected[xmltv_id][0])

    output_path = Path(args.output)
    coverage_path = Path(args.coverage)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_path.parent.mkdir(parents=True, exist_ok=True)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

    matched = set(selected)
    unmatched = sorted(wanted - matched)
    multi_source = sorted(xmltv_id for xmltv_id, items in candidates.items() if len(items) > 1)

    lines = [
        f"playlist tvg-ids: {len(wanted)}",
        f"matched EPG ids: {len(matched)}",
        f"unmatched EPG ids: {len(unmatched)}",
        f"ids with multiple possible EPG sources: {len(multi_source)}",
        f"channel XML parse errors: {len(parse_errors)}",
        "",
        "MATCHED SOURCE SELECTIONS",
    ]
    for xmltv_id in sorted(selected):
        channel, path = selected[xmltv_id]
        lines.append(
            f"{xmltv_id}\t{channel.attrib.get('site','')}\t{channel.attrib.get('site_id','')}\t{path}"
        )

    lines.extend(["", "UNMATCHED IDS"])
    lines.extend(unmatched)

    if parse_errors:
        lines.extend(["", "PARSE ERRORS"])
        lines.extend(parse_errors)

    coverage_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Matched {len(matched)}/{len(wanted)} playlist tvg-ids to iptv-org/epg sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
