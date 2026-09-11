#!/usr/bin/env python3
"""Merge XMLTV guide fragments without loading the whole guide into memory at once."""

from __future__ import annotations

import argparse
import glob
import xml.etree.ElementTree as ET
from pathlib import Path


def xml_bytes(element: ET.Element) -> bytes:
    return ET.tostring(element, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", help="XMLTV files or glob patterns")
    parser.add_argument("--output", default="output/guide.xml")
    args = parser.parse_args()

    files: list[Path] = []
    for pattern in args.inputs:
        matches = sorted(Path(path) for path in glob.glob(pattern))
        if matches:
            files.extend(matches)
        else:
            path = Path(pattern)
            if path.exists():
                files.append(path)

    files = sorted(dict.fromkeys(files))
    if not files:
        parser.error("no XMLTV input files were found")

    # First pass: collect unique channel definitions and root attributes.
    root_attrs: dict[str, str] = {}
    channel_xml: dict[str, bytes] = {}
    valid_files: list[Path] = []

    for path in files:
        try:
            tree = ET.parse(path)
        except (ET.ParseError, OSError) as exc:
            print(f"warning: skipping invalid XMLTV fragment {path}: {exc}")
            continue

        root = tree.getroot()
        if root.tag != "tv":
            print(f"warning: skipping non-XMLTV fragment {path}")
            continue

        if not root_attrs:
            root_attrs = dict(root.attrib)

        for channel in root.findall("channel"):
            channel_id = channel.attrib.get("id", "").strip()
            if channel_id and channel_id not in channel_xml:
                channel_xml[channel_id] = xml_bytes(channel)

        valid_files.append(path)

    if not valid_files:
        parser.error("all XMLTV fragments were invalid")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build the opening <tv> tag while escaping attribute values via ElementTree.
    opening = ET.tostring(ET.Element("tv", root_attrs), encoding="unicode", short_empty_elements=True)
    if opening.endswith(" />"):
        opening = opening[:-3] + ">"
    elif opening.endswith("/>"):
        opening = opening[:-2] + ">"

    programmes = 0
    with output_path.open("wb") as out:
        out.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        out.write(opening.encode("utf-8") + b"\n")

        for channel_id in sorted(channel_xml):
            out.write(b"  " + channel_xml[channel_id] + b"\n")

        # Second pass: stream programme elements one fragment at a time.
        for path in valid_files:
            try:
                tree = ET.parse(path)
            except (ET.ParseError, OSError):
                continue
            root = tree.getroot()
            for programme in root.findall("programme"):
                out.write(b"  " + xml_bytes(programme) + b"\n")
                programmes += 1

        out.write(b"</tv>\n")

    print(
        f"Merged {len(valid_files)} XMLTV fragment(s): "
        f"{len(channel_xml)} channel(s), {programmes} programme(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
