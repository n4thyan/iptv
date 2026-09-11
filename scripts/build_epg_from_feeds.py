#!/usr/bin/env python3
"""Build a fast Kodi XMLTV guide from prebuilt feeds.

EPG providers and IPTV-org often describe the same channel with different ID
punctuation (for example ``Channel.4.HD.uk`` vs ``Channel4.uk@UKHD``). This
builder first honours exact IDs, then uses deliberately conservative,
country-aware compatibility keys. Compatible source rows are rewritten to the
*exact* IPTV-org tvg-id values used by the playlist so Kodi can join the guide
without manual channel mapping.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import shutil
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

USER_AGENT = "Kodi-IPTV-EPG-Builder/2.3"
QUALITY_SUFFIXES = ("uhd", "fhd", "hd", "sd")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

# Some EPGShare datasets encode the dataset name into the final ID suffix
# instead of using a plain ISO country code. Normalize only explicit known
# aliases so the matcher remains country-safe rather than broadly fuzzy.
COUNTRY_ALIASES = {
    "us1": "us",
    "us2": "us",
    "uslocals1": "us",
    "uslocals2": "us",
    "ussports1": "us",
}

# Common UK regional abbreviations used by EPGShare. These are deliberately
# explicit rather than fuzzy so a regional schedule cannot silently jump to a
# different region.
FEED_ALIASES: dict[str, set[str]] = {
    "channelislands": {"channelislands", "ci"},
    "eastmidlands": {"eastmidlands", "eastmid", "emidlands", "emid"},
    "london": {"london", "lon"},
    "northeastcumbria": {"northeastcumbria", "necumbria", "neandc"},
    "northernireland": {"northernireland", "ni"},
    "northwest": {"northwest", "nwest"},
    "scotland": {"scotland", "scot"},
    "southeast": {"southeast", "seast"},
    "south": {"south", "sth"},
    "southwest": {"southwest", "swest"},
    "wales": {"wales", "wal"},
    "westmidlands": {"westmidlands", "wm"},
    "yorkshire": {"yorkshire", "yorks", "yandl"},
}


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


def playlist_base_id(identifier: str) -> str:
    return identifier.split("@", 1)[0].strip()


def split_country_id(identifier: str) -> tuple[str, str] | None:
    """Return (stem, normalized country) for Channel.Name.uk-style IDs."""
    base = playlist_base_id(identifier)
    if "." not in base:
        return None
    stem, country = base.rsplit(".", 1)
    country = NON_ALNUM_RE.sub("", country.casefold())
    country = COUNTRY_ALIASES.get(country, country)
    if not stem or not country:
        return None
    return stem, country


def strip_quality_suffix(value: str) -> str:
    for suffix in QUALITY_SUFFIXES:
        if value.endswith(suffix) and len(value) > len(suffix) + 2:
            return value[: -len(suffix)]
    return value


def normalized_stems(stem: str) -> list[str]:
    """Create conservative punctuation/quality variants for an ID stem."""
    normalized = NON_ALNUM_RE.sub("", stem.casefold())
    if not normalized:
        return []
    values = [normalized]
    stripped = strip_quality_suffix(normalized)
    if stripped and stripped not in values:
        values.append(stripped)
    return values


def compatibility_keys(identifier: str) -> list[tuple[str, str]]:
    parts = split_country_id(identifier)
    if parts is None:
        return []
    stem, country = parts
    return [(country, value) for value in normalized_stems(stem)]


def feed_variants(identifier: str) -> list[str]:
    if "@" not in identifier:
        return []
    feed = NON_ALNUM_RE.sub("", identifier.split("@", 1)[1].casefold())
    if not feed:
        return []
    canonical = strip_quality_suffix(feed)
    values = {feed, canonical}
    values.update(FEED_ALIASES.get(canonical, set()))
    return sorted(value for value in values if value)


def build_target_index(
    requested_ids: set[str],
) -> dict[tuple[str, str], dict[str, set[str]]]:
    """Index base and feed-specific keys while retaining collision information."""
    index: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for target_id in requested_ids:
        base_id = playlist_base_id(target_id)
        parts = split_country_id(target_id)
        if parts is None:
            continue
        stem, country = parts
        base_stems = normalized_stems(stem)

        # Base-level mapping handles ordinary quality differences, such as
        # Channel.4.HD.uk -> Channel4.uk@UKHD.
        for base_stem in base_stems:
            index[(country, base_stem)][base_id].add(target_id)

        # Feed-specific keys handle regional sources such as
        # BBC.One.Lon.HD.uk -> BBCOne.uk@London / LondonHD.
        primary_base = base_stems[-1]
        for feed in feed_variants(target_id):
            index[(country, primary_base + feed)][base_id].add(target_id)
    return index


def targets_for_source_id(
    source_id: str,
    requested_ids: set[str],
    target_index: dict[tuple[str, str], dict[str, set[str]]],
) -> tuple[list[str], str]:
    """Resolve an XMLTV ID to exact playlist IDs without ambiguous fuzzy guessing."""
    if source_id in requested_ids:
        return [source_id], "exact"

    for key in compatibility_keys(source_id):
        base_groups = target_index.get(key, {})
        # Multiple different IPTV-org base channels collapsing to one key is
        # ambiguous. Feed variants of the same base channel are safe to clone.
        if len(base_groups) != 1:
            continue
        targets = next(iter(base_groups.values()))
        if targets:
            return sorted(targets), "compatible"
    return [], "unmatched"


def clone_channel_for_target(element: ET.Element, target_id: str) -> ET.Element:
    clone = clone_element(element)
    clone.set("id", target_id)
    return clone


def clone_programme_for_target(element: ET.Element, target_id: str) -> ET.Element:
    clone = clone_element(element)
    clone.set("channel", target_id)
    return clone


def parse_source(
    path: Path,
    requested_ids: set[str],
    target_index: dict[tuple[str, str], dict[str, set[str]]],
    channel_elements: dict[str, ET.Element],
    programmes: list[ET.Element],
    seen_programmes: set[tuple[str, str, str, str]],
    programmed_ids: set[str],
) -> dict[str, int]:
    kept_channels = 0
    kept_programmes = 0
    exact_source_channels: set[str] = set()
    compatible_source_channels: set[str] = set()
    unmatched_source_channels: set[str] = set()
    opener = gzip.open if path.suffix.casefold() == ".gz" else open
    resolved: dict[str, tuple[list[str], str]] = {}

    def resolve(source_id: str) -> tuple[list[str], str]:
        if source_id not in resolved:
            resolved[source_id] = targets_for_source_id(source_id, requested_ids, target_index)
        return resolved[source_id]

    with opener(path, "rb") as handle:
        for _event, element in ET.iterparse(handle, events=("end",)):
            tag = local_name(element.tag)
            if tag == "channel":
                source_id = element.attrib.get("id", "").strip()
                targets, mode = resolve(source_id)
                if mode == "exact":
                    exact_source_channels.add(source_id)
                elif mode == "compatible":
                    compatible_source_channels.add(source_id)
                elif source_id:
                    unmatched_source_channels.add(source_id)

                for target_id in targets:
                    if target_id not in channel_elements:
                        channel_elements[target_id] = clone_channel_for_target(element, target_id)
                        kept_channels += 1
                element.clear()

            elif tag == "programme":
                source_id = element.attrib.get("channel", "").strip()
                targets, mode = resolve(source_id)
                if mode == "exact":
                    exact_source_channels.add(source_id)
                elif mode == "compatible":
                    compatible_source_channels.add(source_id)
                elif source_id:
                    unmatched_source_channels.add(source_id)

                title = child_text(element, "title")
                for target_id in targets:
                    signature = (
                        target_id,
                        element.attrib.get("start", ""),
                        element.attrib.get("stop", ""),
                        title,
                    )
                    if signature in seen_programmes:
                        continue
                    seen_programmes.add(signature)
                    programmes.append(clone_programme_for_target(element, target_id))
                    programmed_ids.add(target_id)
                    kept_programmes += 1
                element.clear()

    return {
        "channels": kept_channels,
        "programmes": kept_programmes,
        "exact_source_ids": len(exact_source_channels),
        "compatible_source_ids": len(compatible_source_channels),
        "unmatched_source_ids": len(unmatched_source_channels),
    }


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

    target_index = build_target_index(requested_ids)
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
                future = executor.submit(download_source, source, destination, args.download_timeout)
                future_map[future] = (index, source)

            for future in as_completed(future_map):
                index, source = future_map[future]
                try:
                    path = future.result()
                    downloads[index] = path
                    source_stats.append(
                        {"source": source, "downloaded": True, "bytes": path.stat().st_size}
                    )
                except Exception as exc:
                    failures.append(f"download\t{source}\t{exc}")
                    source_stats.append(
                        {"source": source, "downloaded": False, "error": str(exc)}
                    )

        for index, source in enumerate(sources, start=1):
            path = downloads.get(index)
            if path is None:
                continue
            try:
                parsed = parse_source(
                    path,
                    requested_ids,
                    target_index,
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
                    item.update(
                        {
                            "matched_channel_elements": parsed["channels"],
                            "matched_programmes": parsed["programmes"],
                            "exact_source_ids": parsed["exact_source_ids"],
                            "compatible_source_ids": parsed["compatible_source_ids"],
                            "unmatched_source_ids": parsed["unmatched_source_ids"],
                        }
                    )
                    break

    if not programmes:
        failures_path.parent.mkdir(parents=True, exist_ok=True)
        failures_path.write_text(
            ("\n".join(failures) + "\n") if failures else "",
            encoding="utf-8",
        )
        raise SystemExit("no programme data matched the playlist IDs")

    write_guide(output_path, channel_elements, programmes, programmed_ids)

    unmatched = sorted(requested_ids - programmed_ids)
    matched = sorted(programmed_ids)
    stats = {
        "requested_playlist_ids": len(requested_ids),
        "sources_configured": len(sources),
        "sources_downloaded": sum(1 for item in source_stats if item.get("downloaded")),
        "sources_failed": sum(
            1
            for item in source_stats
            if not item.get("downloaded") or item.get("parse_error")
        ),
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
