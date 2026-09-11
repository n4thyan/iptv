#!/usr/bin/env python3
"""Split a large iptv-org/epg custom channel file into smaller batches.

The upstream grabber builds an in-memory work queue for every channel/day. Feeding
it the entire English playlist at once can exceed Node's default heap. Splitting
the channel file keeps each grabber process small and lets the workflow merge the
finished XMLTV fragments afterwards.
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def clone_element(element: ET.Element) -> ET.Element:
    return ET.fromstring(ET.tostring(element, encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="output/epg.channels.xml")
    parser.add_argument("--output-dir", default="output/epg-chunks")
    parser.add_argument("--size", type=int, default=75)
    parser.add_argument("--manifest", default="output/epg-chunks.json")
    args = parser.parse_args()

    if args.size < 1:
        parser.error("--size must be at least 1")

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Remove stale chunks from previous local runs.
    for stale in output_dir.glob("chunk-*.channels.xml"):
        stale.unlink()

    root = ET.parse(input_path).getroot()
    channels = list(root.findall("channel"))
    chunks: list[dict[str, object]] = []

    for chunk_index, start in enumerate(range(0, len(channels), args.size), start=1):
        subset = channels[start : start + args.size]
        chunk_root = ET.Element("channels")
        for channel in subset:
            chunk_root.append(clone_element(channel))

        filename = f"chunk-{chunk_index:03d}.channels.xml"
        path = output_dir / filename
        tree = ET.ElementTree(chunk_root)
        ET.indent(tree, space="  ")
        tree.write(path, encoding="utf-8", xml_declaration=True)
        chunks.append({"file": str(path), "channels": len(subset)})

    manifest = {
        "source": str(input_path),
        "channels": len(channels),
        "chunk_size": args.size,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(
        f"Split {len(channels)} EPG channels into {len(chunks)} chunk(s) "
        f"of at most {args.size}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
