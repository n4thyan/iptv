#!/usr/bin/env python3
"""Build a fast, exact-ID XMLTV guide from prebuilt XMLTV feeds.

This is the default production path for the Kodi project.  It deliberately avoids
scraping thousands of channels provider-by-provider.  Instead it downloads a
small curated set of already-generated XMLTV feeds, keeps only programme data
whose channel IDs exactly match tvg-id values in our playlist, de-duplicates
programme rows and writes a compact guide suitable for Kodi.
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

USER_AGENT = "Kodi-IPTV-EPG-Builder/2.0"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def clone_element(element: ET.Element) -> ET.Element:
    return ET.fromstring(ET.tostring(element, encoding="utf-8"))


def load_ids(path: Path) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def load_sources(path: Path) -> list[str]:
    sources: list[str] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        sources.append(line)
    return sources


def download_source(source: str, destination: Path, timeout: int) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            with destination.open("wb") as output:
                shutil.copyfileobj(response, output, length=1024 * 1024)
    else:
        shutil.copy2(Path(source), destination)
    if not destination.exists() or destination.stat().st_size == 0:
        raise RuntimeError("download produced an empty file")
    return destination


def source_suffix(source: str) -> str:
    path = urlparse(source).path if source.startswith(("http://", "https://")) else source
    return ".xml.gz" if path.casefold().endswith(".gz") else ".xml"


def child_text(element: ET.Element, wanted: str) -> str:
    for child in element:
        if local_name(child.tag) == wanted:
            return (child.text or "").strip()
    return ""


def parse_source(
    path: Path,
    requested_ids: set[str],
    channel_elements: dict[str, ET.Element],
    programmes: list[ET.Element],
    seen_programmes: set[tuple[str, str, str, str]],
    programmed_ids: set[str],
) -> dict[str, int]:
    kept_channels = 0
    kept_programmes = 0
    opener = gzip.open if path.suffix.casefold() == ".gz" else open

    with opener(path, "rb") as handle:
        for _event, element in ET.iterparse(handle, events=("end",)):
            tag = local_name(element.tag)
            if tag == "channel":
                channel_id = element.attrib.get("id", "").strip()
                if channel_id in requested_ids and channel_id not in channel_elements:
                    channel_elements[channel_id] = clone_element(element)
                    kept_channels += 1
            elif tag == "programme":
                channel_id = element.attrib.get("channel", "").strip()
                if channel_id in requested_ids:
                    signature = (
                        channel_id,
                        element.attrib.get("start", ""),
                        element.attrib.get("stop", ""),
                        child_text(element, "title"),
                    )
                    if signature not in seen_programmes:
                        seen_programmes.add(signature)
                        programmes.append(clone_element(element))
                        programmed_ids.add(channel_id)
                        kept_programmes += 1
            element.clear()

    return {"channels": kept_channels, "programmes": kept_programmes}


def write_guide(
    output: Path,
    channel_elements: dict[str, ET.Element],
    programmes: list[ET.Element],
    programmed_ids: set[str],
) -> None:
    root = ET.Element("tv", {"generator-info-name": "n4thyan/iptv fast XMLTV builder"})

    for channel_id in sorted(programmed_ids):
        channel = channel_elements.get(channel_id)
        if channel is None:
            channel = ET.Element("channel", {"id": channel_id})
            display_name = ET.SubElement(channel, "display-name")
            display_name.text = channel_id
        root.append(channel)

    programmes.sort(
        key=lambda item: (
            item.attrib.get("channel", ""),
            item.attrib.get("start", ""),
            item.attrib.get("stop", ""),
        )
    )
    for programme in programmes:
        root.append(programme)

    output.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", required=True)
    parser.add_argument("--sources-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--stats", required=True)
    parser.add_argument("--coverage", required=True)
    parser.add_argument("--failures", required=True)
    parser.add_argument("--download-workers", type=int, default=6)
    parser.add_argument("--download-timeout", type=int, default=90)
    args = parser.parse_args()

    if args.download_workers < 1:
        parser.error("--download-workers must be at least 1")
    if args.download_timeout < 5:
        parser.error("--download-timeout must be at least 5 seconds")

    ids_path = Path(args.ids).resolve()
    sources_file = Path(args.sources_file).resolve()
    output_path = Path(args.output).resolve()
    stats_path = Path(args.stats).resolve()
    coverage_path = Path(args.coverage).resolve()
    failures_path = Path(args.failures).resolve()

    requested_ids = load_ids(ids_path)
    sources = load_sources(sources_file)
    if not requested_ids:
        raise SystemExit("playlist ID file is empty")
    if not sources:
        raise SystemExit("EPG source list is empty")

    channel_elements: dict[str, ET.Element] = {}
    programmes: list[ET.Element] = []
    seen_programmes: set[tuple[str, str, str, str]] = set()
    programmed_ids: set[str] = set()
    failures: list[str] = []
    source_stats: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="iptv-epg-") as temp_name:
        temp_dir = Path(temp_name)
        downloads: dict[int, Path] = {}
        workers = min(args.download_workers, len(sources))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {}
            for index, source in enumerate(sources, start=1):
                destination = temp_dir / f"source-{index:03d}{source_suffix(source)}"
                future = executor.submit(
                    download_source,
                    source,
                    destination,
                    args.download_timeout,
                )
                future_map[future] = (index, source)

            for future in as_completed(future_map):
                index, source = future_map[future]
                try:
                    path = future.result()
                    downloads[index] = path
                    source_stats.append(
                        {
                            "source": source,
                            "downloaded": True,
                            "bytes": path.stat().st_size,
                        }
                    )
                except Exception as exc:
                    failures.append(f"download\t{source}\t{exc}")
                    source_stats.append(
                        {
                            "source": source,
                            "downloaded": False,
                            "error": str(exc),
                        }
                    )

        for index, source in enumerate(sources, start=1):
            path = downloads.get(index)
            if path is None:
                continue
            try:
                parsed = parse_source(
                    path,
                    requested_ids,
                    channel_elements,
                    programmes,
                    seen_programmes,
                    programmed_ids,
                )
            except Exception as exc:
                failures.append(f"parse\t{source}\t{exc}")
                for item in source_stats:
                    if item.get("source") == source:
                        item["parse_error"] = str(exc)
                        break
                continue

            for item in source_stats:
                if item.get("source") == source:
                    item["matched_channel_elements"] = parsed["channels"]
                    item["matched_programmes"] = parsed["programmes"]
                    break

    if not programmes:
        failures_path.parent.mkdir(parents=True, exist_ok=True)
        failures_path.write_text("\n".join(failures) + "\n", encoding="utf-8")
        raise SystemExit("no programme data matched the playlist IDs")

    write_guide(output_path, channel_elements, programmes, programmed_ids)

    unmatched = sorted(requested_ids - programmed_ids)
    matched = sorted(programmed_ids)
    stats = {
        "requested_playlist_ids": len(requested_ids),
        "sources_configured": len(sources),
        "sources_downloaded": sum(1 for item in source_stats if item.get("downloaded")),
        "sources_failed": sum(1 for item in source_stats if not item.get("downloaded") or item.get("parse_error")),
        "channel_elements": len(programmed_ids),
        "programme_elements": len(programmes),
        "channels_with_programmes": len(programmed_ids),
        "playlist_ids_without_programmes": len(unmatched),
        "source_details": source_stats,
    }

    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")

    coverage_lines = [
        f"playlist tvg-ids: {len(requested_ids)}",
        f"channels with programmes: {len(programmed_ids)}",
        f"playlist ids without programme data: {len(unmatched)}",
        f"EPG feeds configured: {len(sources)}",
        f"EPG feeds downloaded: {stats['sources_downloaded']}",
        f"EPG feeds failed: {stats['sources_failed']}",
        "",
        "MATCHED IDS",
        *matched,
        "",
        "UNMATCHED IDS",
        *unmatched,
        "",
    ]
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_path.write_text("\n".join(coverage_lines), encoding="utf-8")

    failures_path.parent.mkdir(parents=True, exist_ok=True)
    failures_path.write_text(
        ("\n".join(failures) + "\n") if failures else "",
        encoding="utf-8",
    )

    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
