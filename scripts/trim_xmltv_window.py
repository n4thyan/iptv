#!/usr/bin/env python3
"""Trim a full XMLTV guide to a small rolling window for Kodi on Xbox.

The full merged guide is useful for diagnostics and desktop Kodi, but importing
many days of programme rows on Xbox can make PVR startup unnecessarily heavy.
This script keeps all channel definitions while retaining only programmes that
overlap a configurable time window around the current UTC time.
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

TIME_RE = re.compile(r"^(\d{8,14})(?:\s*([+-]\d{4}))?")


def parse_xmltv_time(value: str) -> datetime | None:
    """Parse common XMLTV timestamps into timezone-aware UTC datetimes."""
    match = TIME_RE.match((value or "").strip())
    if not match:
        return None

    stamp, offset = match.groups()
    formats = {
        8: "%Y%m%d",
        10: "%Y%m%d%H",
        12: "%Y%m%d%H%M",
        14: "%Y%m%d%H%M%S",
    }
    fmt = formats.get(len(stamp))
    if fmt is None:
        return None

    try:
        dt = datetime.strptime(stamp, fmt)
    except ValueError:
        return None

    if offset:
        sign = 1 if offset[0] == "+" else -1
        hours = int(offset[1:3])
        minutes = int(offset[3:5])
        tz = timezone(sign * timedelta(hours=hours, minutes=minutes))
        dt = dt.replace(tzinfo=tz)
    else:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def overlaps_window(programme: ET.Element, window_start: datetime, window_end: datetime) -> bool:
    start = parse_xmltv_time(programme.attrib.get("start", ""))
    if start is None:
        return False

    stop = parse_xmltv_time(programme.attrib.get("stop", ""))
    if stop is None or stop <= start:
        stop = start + timedelta(hours=6)

    return stop >= window_start and start <= window_end


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--stats", required=True)
    parser.add_argument("--past-hours", type=int, default=3)
    parser.add_argument("--future-hours", type=int, default=36)
    args = parser.parse_args()

    if args.past_hours < 0:
        parser.error("--past-hours cannot be negative")
    if args.future_hours < 1:
        parser.error("--future-hours must be at least 1")

    input_path = Path(args.input)
    output_path = Path(args.output)
    stats_path = Path(args.stats)

    root = ET.parse(input_path).getroot()
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=args.past_hours)
    window_end = now + timedelta(hours=args.future_hours)

    channels = [item for item in root if item.tag.rsplit("}", 1)[-1] == "channel"]
    programmes = [item for item in root if item.tag.rsplit("}", 1)[-1] == "programme"]
    kept_programmes = [
        programme
        for programme in programmes
        if overlaps_window(programme, window_start, window_end)
    ]

    output_root = ET.Element("tv", dict(root.attrib))
    output_root.set("generator-info-name", "n4thyan/iptv Xbox XMLTV builder")
    for channel in channels:
        output_root.append(channel)
    for programme in kept_programmes:
        output_root.append(programme)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(output_root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

    kept_channel_ids = {
        item.attrib.get("channel", "")
        for item in kept_programmes
        if item.attrib.get("channel")
    }
    stats = {
        "generated_at_utc": now.isoformat(),
        "past_hours": args.past_hours,
        "future_hours": args.future_hours,
        "input_channels": len(channels),
        "input_programmes": len(programmes),
        "output_channels": len(channels),
        "channels_with_programmes_in_window": len(kept_channel_ids),
        "output_programmes": len(kept_programmes),
        "programme_reduction_percent": round(
            (1 - (len(kept_programmes) / len(programmes))) * 100, 2
        ) if programmes else 0.0,
    }
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
