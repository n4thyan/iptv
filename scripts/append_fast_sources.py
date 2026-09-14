#!/usr/bin/env python3
"""Append maintained FAST-service playlists to an existing Kodi M3U.

Each source is supplied as NAME=URL. Entries are preserved, tagged with a
service group, de-duplicated by stream URL, and their tvg-id values are added
to the channel-id file consumed by the EPG builder.
"""

from __future__ import annotations

import argparse
import re
import urllib.request
from pathlib import Path

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
GROUP_RE = re.compile(r'group-title="([^"]*)"')
ADULT_TERMS = ("xxx", "porn", "porno", "adult", "babestation", "playboy", "redlight")


def fetch_text(source: str) -> str:
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(source, headers={"User-Agent": "Kodi-IPTV-FAST/1.0"})
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.read().decode("utf-8-sig", errors="replace")
    return Path(source).read_text(encoding="utf-8-sig")


def parse_source(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--source must use NAME=URL")
    name, url = value.split("=", 1)
    name, url = name.strip(), url.strip()
    if not name or not url:
        raise argparse.ArgumentTypeError("--source must use non-empty NAME=URL")
    return name, url


def add_service_group(extinf: str, service: str) -> str:
    match = GROUP_RE.search(extinf)
    service_group = f"FAST - {service}"
    if match:
        groups = [item.strip() for item in match.group(1).split(";") if item.strip()]
        if service_group.casefold() not in {item.casefold() for item in groups}:
            groups.append(service_group)
        return extinf[: match.start(1)] + ";".join(groups) + extinf[match.end(1) :]
    comma = extinf.find(",")
    addition = f' group-title="{service_group}"'
    return extinf + addition if comma < 0 else extinf[:comma] + addition + extinf[comma:]


def stanzas(text: str):
    lines = [line.strip() for line in text.splitlines()]
    i = 0
    while i < len(lines):
        if not lines[i].startswith("#EXTINF"):
            i += 1
            continue
        stanza = [lines[i]]
        i += 1
        while i < len(lines):
            line = lines[i]
            if line.startswith("#EXTINF"):
                break
            if line:
                stanza.append(line)
            i += 1
            if line and not line.startswith("#"):
                break
        if len(stanza) >= 2 and not stanza[-1].startswith("#"):
            yield stanza


def is_adult(extinf: str) -> bool:
    lowered = extinf.casefold()
    return any(term in lowered for term in ADULT_TERMS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", required=True)
    parser.add_argument("--ids", required=True)
    parser.add_argument("--source", action="append", type=parse_source, default=[])
    args = parser.parse_args()

    playlist_path = Path(args.playlist)
    ids_path = Path(args.ids)
    original = playlist_path.read_text(encoding="utf-8-sig").rstrip("\n")
    existing_urls = {
        line.strip() for line in original.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    ids = {
        line.strip() for line in ids_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    appended: list[str] = []
    source_counts: dict[str, int] = {}
    skipped_duplicates = 0
    skipped_adult = 0

    for service, source in args.source:
        count = 0
        for stanza in stanzas(fetch_text(source)):
            extinf = stanza[0]
            url = stanza[-1]
            if is_adult(extinf):
                skipped_adult += 1
                continue
            if url in existing_urls:
                skipped_duplicates += 1
                continue
            attrs = dict(ATTR_RE.findall(extinf))
            tvg_id = attrs.get("tvg-id", "").strip()
            stanza[0] = add_service_group(extinf, service)
            appended.extend(stanza)
            existing_urls.add(url)
            if tvg_id:
                ids.add(tvg_id)
            count += 1
        source_counts[service] = count

    if appended:
        playlist_path.write_text(original + "\n" + "\n".join(appended) + "\n", encoding="utf-8")
    ids_path.write_text("\n".join(sorted(ids)) + "\n", encoding="utf-8")

    print(f"FAST entries appended: {sum(source_counts.values())}")
    for service, count in source_counts.items():
        print(f"  {service}: {count}")
    print(f"duplicate stream URLs skipped: {skipped_duplicates}")
    print(f"adult entries skipped: {skipped_adult}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
