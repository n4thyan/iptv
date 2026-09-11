#!/usr/bin/env python3
"""Build a custom iptv-org/epg channels file for the English playlist.

The IPTV-org playlist and iptv-org/epg normally share channel identifiers. This
script selects one EPG source for each playlist tvg-id where possible.

If an exact feed ID is unavailable, it can safely alias a closely related feed
of the same base channel by rewriting the EPG output ID to the playlist's tvg-id.
That improves coverage for cases such as a playlist using ``BBCOne.uk`` while a
provider only exposes regional IDs such as ``BBCOne.uk@London``.
"""

from __future__ import annotations

import argparse
import difflib
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Candidate:
    channel: ET.Element
    path: Path
    source_xmltv_id: str


def load_ids(path: Path) -> set[str]:
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def base_id(xmltv_id: str) -> str:
    return xmltv_id.split("@", 1)[0]


def candidate_score(target: str, candidate: Candidate) -> tuple[int, int, float, str, str]:
    channel = candidate.channel
    lang = channel.attrib.get("lang", "").casefold()
    lang_score = 0 if lang == "en" else 1

    source_id = candidate.source_xmltv_id
    exact_score = 0 if source_id == target else 1

    # For aliases, prefer an ID textually similar to the target and then shorter
    # feed suffixes (e.g. @HD before highly specific regional variants).
    similarity = difflib.SequenceMatcher(None, target.casefold(), source_id.casefold()).ratio()
    length_delta = abs(len(source_id) - len(target))
    site = channel.attrib.get("site", "")
    return (exact_score, lang_score, length_delta, -similarity, site.casefold(), str(candidate.path).casefold())


def clone_for_target(candidate: Candidate, target: str) -> ET.Element:
    cloned = ET.Element("channel", dict(candidate.channel.attrib))
    cloned.attrib["xmltv_id"] = target
    cloned.text = candidate.channel.text or ""
    return cloned


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", default="output/channel_ids.txt")
    parser.add_argument("--sites-root", required=True)
    parser.add_argument("--output", default="output/epg.channels.xml")
    parser.add_argument("--coverage", default="output/epg-coverage.txt")
    args = parser.parse_args()

    wanted = load_ids(Path(args.ids))
    wanted_bases = {base_id(xmltv_id) for xmltv_id in wanted}
    sites_root = Path(args.sites_root)

    exact_candidates: dict[str, list[Candidate]] = defaultdict(list)
    base_candidates: dict[str, list[Candidate]] = defaultdict(list)
    parse_errors: list[str] = []

    # Load only channel definitions that could possibly match one of our base IDs.
    for path in sorted(sites_root.rglob("*.channels.xml")):
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            parse_errors.append(f"{path}: {exc}")
            continue

        for channel in root.findall("channel"):
            xmltv_id = channel.attrib.get("xmltv_id", "").strip()
            if not xmltv_id:
                continue
            base = base_id(xmltv_id)
            if base not in wanted_bases:
                continue

            stored = ET.Element("channel", dict(channel.attrib))
            stored.text = channel.text or ""
            candidate = Candidate(stored, path, xmltv_id)
            base_candidates[base].append(candidate)
            if xmltv_id in wanted:
                exact_candidates[xmltv_id].append(candidate)

    # target -> (output channel, source path, original source ID, match mode)
    selected: dict[str, tuple[ET.Element, Path, str, str]] = {}

    for target in sorted(wanted):
        pool = exact_candidates.get(target, [])
        mode = "exact"

        if not pool:
            # Only alias within the same IPTV-org base channel. This avoids fuzzy
            # matching unrelated networks merely because their names look alike.
            pool = base_candidates.get(base_id(target), [])
            mode = "alias"

        if not pool:
            continue

        best = sorted(pool, key=lambda candidate: candidate_score(target, candidate))[0]
        selected[target] = (
            clone_for_target(best, target),
            best.path,
            best.source_xmltv_id,
            mode if best.source_xmltv_id != target else "exact",
        )

    root = ET.Element("channels")
    for target in sorted(selected):
        root.append(selected[target][0])

    output_path = Path(args.output)
    coverage_path = Path(args.coverage)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_path.parent.mkdir(parents=True, exist_ok=True)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

    matched = set(selected)
    unmatched = sorted(wanted - matched)
    aliased = sorted(target for target, value in selected.items() if value[3] == "alias")
    multi_source = sorted(
        target
        for target in wanted
        if len(exact_candidates.get(target, [])) > 1
        or (not exact_candidates.get(target) and len(base_candidates.get(base_id(target), [])) > 1)
    )

    lines = [
        f"playlist tvg-ids: {len(wanted)}",
        f"matched EPG ids: {len(matched)}",
        f"exact EPG matches: {len(matched) - len(aliased)}",
        f"same-channel alias matches: {len(aliased)}",
        f"unmatched EPG ids: {len(unmatched)}",
        f"ids with multiple possible EPG sources: {len(multi_source)}",
        f"channel XML parse errors: {len(parse_errors)}",
        "",
        "MATCHED SOURCE SELECTIONS",
        "target_tvg_id\tmode\tsource_xmltv_id\tsite\tsite_id\tdefinition_file",
    ]

    for target in sorted(selected):
        channel, path, source_xmltv_id, mode = selected[target]
        lines.append(
            f"{target}\t{mode}\t{source_xmltv_id}\t"
            f"{channel.attrib.get('site','')}\t{channel.attrib.get('site_id','')}\t{path}"
        )

    lines.extend(["", "UNMATCHED IDS"])
    lines.extend(unmatched)

    if parse_errors:
        lines.extend(["", "PARSE ERRORS"])
        lines.extend(parse_errors)

    coverage_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        f"Matched {len(matched)}/{len(wanted)} playlist tvg-ids "
        f"({len(aliased)} via same-channel aliases)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
