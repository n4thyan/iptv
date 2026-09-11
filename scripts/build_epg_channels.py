#!/usr/bin/env python3
"""Build a custom iptv-org/epg channels file for the English playlist.

Matching order is deliberately conservative:

1. exact playlist ``tvg-id`` -> EPG ``xmltv_id``;
2. another feed of the same IPTV-org base channel;
3. an otherwise-unmapped EPG definition whose displayed channel name exactly
   matches one *unique* IPTV-org channel name/alias from our playlist catalog.

The third rule lets us use upstream definitions that have a blank ``xmltv_id``
without fuzzy-guessing unrelated channels.  It is only allowed when the base
channel has one playlist target/feed, so a generic schedule is not silently
copied onto several regional feed variants.

A ranked candidate manifest is also written.  It can be used by later fallback
passes when a provider is mapped correctly but fails to return programmes.
"""

from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Candidate:
    channel: ET.Element
    path: Path
    source_xmltv_id: str
    discovery_mode: str


def load_ids(path: Path) -> set[str]:
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def base_id(xmltv_id: str) -> str:
    return xmltv_id.split("@", 1)[0]


def normalize_name(value: str) -> str:
    """Normalize a display name for exact alias matching, not fuzzy matching."""
    value = html.unescape(value or "")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def load_catalog(path: Path | None) -> dict[str, dict]:
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    channels = data.get("channels", {})
    return channels if isinstance(channels, dict) else {}


def candidate_score(target: str, candidate: Candidate) -> tuple[int, int, int, float, str, str, str]:
    channel = candidate.channel
    mode_score = {"exact": 0, "alias": 1, "name": 2}.get(candidate.discovery_mode, 9)
    lang = channel.attrib.get("lang", "").casefold()
    lang_score = 0 if lang == "en" else 1

    source_id = candidate.source_xmltv_id
    exact_score = 0 if source_id == target else 1
    similarity = (
        difflib.SequenceMatcher(None, target.casefold(), source_id.casefold()).ratio()
        if source_id
        else 0.0
    )
    length_delta = abs(len(source_id) - len(target)) if source_id else 999
    site = channel.attrib.get("site", "")
    site_id = channel.attrib.get("site_id", "")
    return (
        mode_score,
        exact_score,
        lang_score,
        length_delta,
        -similarity,
        site.casefold(),
        site_id.casefold(),
    )


def clone_for_target(candidate: Candidate, target: str) -> ET.Element:
    cloned = ET.Element("channel", dict(candidate.channel.attrib))
    cloned.attrib["xmltv_id"] = target
    cloned.text = candidate.channel.text or ""
    return cloned


def candidate_key(candidate: Candidate) -> tuple[str, str, str, str]:
    return (
        candidate.channel.attrib.get("site", ""),
        candidate.channel.attrib.get("site_id", ""),
        candidate.source_xmltv_id,
        str(candidate.path),
    )


def build_name_index(
    wanted: set[str], catalog: dict[str, dict]
) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    """Return normalized-name -> base IDs and base -> human-readable aliases."""
    name_to_bases: dict[str, set[str]] = defaultdict(set)
    base_names: dict[str, set[str]] = defaultdict(set)

    for target in wanted:
        info = catalog.get(target, {}) if isinstance(catalog.get(target, {}), dict) else {}
        base = str(info.get("base_id") or base_id(target)).strip()
        raw_names = [
            str(info.get("name") or ""),
            str(info.get("playlist_name") or ""),
            *[str(value) for value in info.get("alt_names", []) if value],
        ]
        for raw in raw_names:
            raw = raw.strip()
            norm = normalize_name(raw)
            # Very short labels (TV, 1, A1...) are too collision-prone for an
            # unmapped-name fallback. They can still match via real xmltv_id.
            if len(norm) < 4:
                continue
            name_to_bases[norm].add(base)
            base_names[base].add(raw)

    return name_to_bases, {key: sorted(values) for key, values in base_names.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", default="output/channel_ids.txt")
    parser.add_argument("--sites-root", required=True)
    parser.add_argument("--catalog", default="output/channel-catalog.json")
    parser.add_argument("--output", default="output/epg.channels.xml")
    parser.add_argument("--coverage", default="output/epg-coverage.txt")
    parser.add_argument("--candidates", default="output/epg-candidates.json")
    args = parser.parse_args()

    wanted = load_ids(Path(args.ids))
    wanted_bases = {base_id(xmltv_id) for xmltv_id in wanted}
    targets_by_base: dict[str, set[str]] = defaultdict(set)
    for target in wanted:
        targets_by_base[base_id(target)].add(target)

    sites_root = Path(args.sites_root)
    catalog_path = Path(args.catalog) if args.catalog else None
    catalog = load_catalog(catalog_path)
    name_to_bases, base_names = build_name_index(wanted, catalog)

    exact_candidates: dict[str, list[Candidate]] = defaultdict(list)
    base_candidates: dict[str, list[Candidate]] = defaultdict(list)
    name_candidates: dict[str, list[Candidate]] = defaultdict(list)
    parse_errors: list[str] = []
    blank_definitions_seen = 0
    blank_definitions_uniquely_named = 0

    for path in sorted(sites_root.rglob("*.channels.xml")):
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            parse_errors.append(f"{path}: {exc}")
            continue

        for channel in root.findall("channel"):
            xmltv_id = channel.attrib.get("xmltv_id", "").strip()
            stored = ET.Element("channel", dict(channel.attrib))
            stored.text = channel.text or ""

            if xmltv_id:
                base = base_id(xmltv_id)
                if base not in wanted_bases:
                    continue
                candidate = Candidate(stored, path, xmltv_id, "alias")
                base_candidates[base].append(candidate)
                if xmltv_id in wanted:
                    exact_candidates[xmltv_id].append(
                        Candidate(stored, path, xmltv_id, "exact")
                    )
                continue

            blank_definitions_seen += 1
            if not catalog:
                continue
            normalized = normalize_name(stored.text or "")
            possible_bases = name_to_bases.get(normalized, set())
            if len(possible_bases) != 1:
                continue
            base = next(iter(possible_bases))
            # A generic blank-ID schedule is only safe when this base channel has
            # one playlist feed. Regional/multi-feed variants must keep using
            # explicit ID-based definitions.
            if len(targets_by_base.get(base, set())) != 1:
                continue
            blank_definitions_uniquely_named += 1
            name_candidates[base].append(Candidate(stored, path, "", "name"))

    ranked_by_target: dict[str, list[Candidate]] = {}
    selected: dict[str, tuple[ET.Element, Path, str, str]] = {}

    for target in sorted(wanted):
        base = base_id(target)
        candidates: list[Candidate] = []
        candidates.extend(exact_candidates.get(target, []))
        candidates.extend(base_candidates.get(base, []))
        if len(targets_by_base.get(base, set())) == 1:
            candidates.extend(name_candidates.get(base, []))

        deduped: dict[tuple[str, str, str, str], Candidate] = {}
        for candidate in candidates:
            key = candidate_key(candidate)
            existing = deduped.get(key)
            if existing is None or candidate_score(target, candidate) < candidate_score(target, existing):
                deduped[key] = candidate

        ranked = sorted(deduped.values(), key=lambda item: candidate_score(target, item))
        ranked_by_target[target] = ranked
        if not ranked:
            continue
        best = ranked[0]
        mode = best.discovery_mode
        if best.source_xmltv_id == target:
            mode = "exact"
        selected[target] = (
            clone_for_target(best, target),
            best.path,
            best.source_xmltv_id,
            mode,
        )

    root = ET.Element("channels")
    for target in sorted(selected):
        root.append(selected[target][0])

    output_path = Path(args.output)
    coverage_path = Path(args.coverage)
    candidates_path = Path(args.candidates)
    for path in (output_path, coverage_path, candidates_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

    candidate_manifest: dict[str, list[dict[str, str]]] = {}
    for target, ranked in sorted(ranked_by_target.items()):
        candidate_manifest[target] = [
            {
                "mode": candidate.discovery_mode,
                "source_xmltv_id": candidate.source_xmltv_id,
                "site": candidate.channel.attrib.get("site", ""),
                "site_id": candidate.channel.attrib.get("site_id", ""),
                "lang": candidate.channel.attrib.get("lang", ""),
                "name": candidate.channel.text or "",
                "definition_file": str(candidate.path),
            }
            for candidate in ranked
        ]
    candidates_path.write_text(
        json.dumps(
            {
                "playlist_tvg_ids": len(wanted),
                "targets_with_candidates": sum(1 for values in candidate_manifest.values() if values),
                "candidates": candidate_manifest,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    matched = set(selected)
    unmatched = sorted(wanted - matched)
    match_modes: dict[str, int] = defaultdict(int)
    for _target, value in selected.items():
        match_modes[value[3]] += 1
    multi_source = sorted(target for target, values in ranked_by_target.items() if len(values) > 1)

    lines = [
        f"playlist tvg-ids: {len(wanted)}",
        f"matched EPG ids: {len(matched)}",
        f"exact EPG matches: {match_modes.get('exact', 0)}",
        f"same-channel alias matches: {match_modes.get('alias', 0)}",
        f"unique-name unmapped-definition matches: {match_modes.get('name', 0)}",
        f"unmatched EPG ids: {len(unmatched)}",
        f"ids with multiple possible EPG sources: {len(multi_source)}",
        f"blank xmltv_id definitions scanned: {blank_definitions_seen}",
        f"blank definitions with safe unique-name candidates: {blank_definitions_uniquely_named}",
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

    if base_names:
        lines.extend(["", "CATALOG ALIASES USED FOR SAFE NAME MATCHING"])
        for base in sorted(base_names):
            lines.append(f"{base}\t{' | '.join(base_names[base])}")

    if parse_errors:
        lines.extend(["", "PARSE ERRORS"])
        lines.extend(parse_errors)

    coverage_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        f"Matched {len(matched)}/{len(wanted)} playlist tvg-ids: "
        f"{match_modes.get('exact', 0)} exact, "
        f"{match_modes.get('alias', 0)} same-channel aliases, "
        f"{match_modes.get('name', 0)} safe unique-name fallbacks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
