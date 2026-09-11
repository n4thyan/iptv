#!/usr/bin/env python3
"""Validate IPTV streams from the user's own network without risking good channels.

Why this is a local tool instead of a GitHub Action:
GitHub-hosted runners may be in a different country, so a perfectly good UK-only
stream can look geo-blocked from the runner. Running this on the PC tests the same
network/region the Xbox will actually use.

The tool:
- preserves complete M3U stanzas (EXTINF + Kodi/VLC directives + URL)
- probes streams in parallel with ffprobe
- understands common referrer/user-agent directives
- classifies access-restricted streams separately from dead streams
- keeps failure history between runs
- can write a cleaned playlist while avoiding one-failure deletions

It never drops geo/access-restricted streams automatically.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote_plus
from urllib.request import Request, urlopen

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
HTTP_STATUS_RE = re.compile(r"(?:HTTP[^\n]*?\s|Server returned\s)(\d{3})", re.IGNORECASE)


@dataclass
class Entry:
    number: int
    lines: list[str]
    url: str
    name: str
    tvg_id: str


@dataclass
class ProbeResult:
    key: str
    name: str
    tvg_id: str
    url: str
    status: str
    detail: str
    attempts: int
    elapsed_seconds: float
    consecutive_failures: int = 0
    drop: bool = False


def load_text(source: str) -> str:
    if source.startswith(("http://", "https://")):
        req = Request(source, headers={"User-Agent": "Kodi-IPTV-Validator/1.0"})
        with urlopen(req, timeout=60) as response:
            return response.read().decode("utf-8-sig", errors="replace")
    return Path(source).read_text(encoding="utf-8-sig")


def parse_playlist(text: str) -> tuple[str, list[Entry]]:
    lines = [line.rstrip("\r") for line in text.splitlines()]
    header = next((line.strip() for line in lines if line.strip().startswith("#EXTM3U")), "#EXTM3U")
    entries: list[Entry] = []
    i = 0
    number = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("#EXTINF"):
            i += 1
            continue

        stanza = [line]
        j = i + 1
        stream_url = ""
        while j < len(lines):
            raw = lines[j].strip()
            if not raw:
                j += 1
                continue
            if raw.startswith("#EXTINF"):
                break
            stanza.append(raw)
            j += 1
            if not raw.startswith("#"):
                stream_url = raw
                break

        if stream_url:
            attrs = dict(ATTR_RE.findall(line))
            name = line.rsplit(",", 1)[-1].strip() if "," in line else ""
            number += 1
            entries.append(
                Entry(
                    number=number,
                    lines=stanza,
                    url=stream_url,
                    name=name,
                    tvg_id=attrs.get("tvg-id", "").strip(),
                )
            )
            i = j
        else:
            i = max(j, i + 1)

    return header, entries


def split_kodi_url(url: str) -> tuple[str, dict[str, str]]:
    if "|" not in url:
        return url, {}
    base, raw_headers = url.split("|", 1)
    headers: dict[str, str] = {}
    for pair in raw_headers.split("&"):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        headers[key.strip().lower()] = unquote_plus(value.strip())
    return base, headers


def stanza_headers(entry: Entry) -> tuple[str | None, dict[str, str]]:
    user_agent: str | None = None
    headers: dict[str, str] = {}

    _, kodi_headers = split_kodi_url(entry.url)
    for key, value in kodi_headers.items():
        if key in {"user-agent", "user_agent"}:
            user_agent = value
        elif key in {"referrer", "referer"}:
            headers["Referer"] = value
        elif key.startswith("!"):
            headers[key[1:]] = value
        else:
            headers[key] = value

    for line in entry.lines[1:-1]:
        lowered = line.casefold()
        if lowered.startswith("#extvlcopt:http-user-agent="):
            user_agent = line.split("=", 1)[1].strip()
        elif lowered.startswith("#extvlcopt:http-referrer="):
            headers["Referer"] = line.split("=", 1)[1].strip()

    return user_agent, headers


def entry_key(entry: Entry) -> str:
    return f"{entry.tvg_id}\t{entry.url}" if entry.tvg_id else entry.url


def classify_failure(stderr: str, timed_out: bool) -> tuple[str, str]:
    text = (stderr or "").strip()
    lower = text.casefold()

    if timed_out:
        return "temporary_failed", "probe timeout"

    status_codes = {int(code) for code in HTTP_STATUS_RE.findall(text)}
    if status_codes & {401, 403, 451} or any(
        token in lower for token in ("forbidden", "unauthorized", "geo-block", "geoblock")
    ):
        code_text = "/".join(str(code) for code in sorted(status_codes & {401, 403, 451}))
        return "access_restricted", f"HTTP {code_text}" if code_text else "access restricted"

    if status_codes & {404, 410}:
        code_text = "/".join(str(code) for code in sorted(status_codes & {404, 410}))
        return "dead", f"HTTP {code_text}"

    if any(token in lower for token in ("404 not found", "410 gone")):
        return "dead", "remote endpoint reports not found/gone"

    if any(
        token in lower
        for token in (
            "connection refused",
            "no route to host",
            "name or service not known",
            "temporary failure in name resolution",
            "could not resolve host",
            "network is unreachable",
        )
    ):
        return "temporary_failed", text[-300:] or "network failure"

    return "temporary_failed", text[-300:] or "ffprobe failed"


def run_one_probe(entry: Entry, timeout: float) -> tuple[str, str, float]:
    base_url, _ = split_kodi_url(entry.url)

    # IPTV Simple can resolve web-page scraper entries that ffprobe cannot.
    if base_url.startswith("@") or any(line.startswith("#WEBPROP") for line in entry.lines):
        return "untested", "Kodi web-scraper entry", 0.0

    user_agent, headers = stanza_headers(entry)
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-rw_timeout",
        str(int(timeout * 1_000_000)),
    ]
    if user_agent:
        cmd.extend(["-user_agent", user_agent])
    if headers:
        header_blob = "".join(f"{key}: {value}\r\n" for key, value in headers.items())
        cmd.extend(["-headers", header_blob])
    cmd.extend(
        [
            "-show_entries",
            "format=format_name",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            base_url,
        ]
    )

    started = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 4,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - started
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        status, detail = classify_failure(stderr, True)
        return status, detail, elapsed

    elapsed = time.monotonic() - started
    if proc.returncode == 0:
        detected = proc.stdout.strip().replace("\n", ", ")
        return "working", detected or "ffprobe opened stream", elapsed

    status, detail = classify_failure(proc.stderr, False)
    return status, detail, elapsed


def probe_entry(entry: Entry, timeout: float, attempts: int, retry_delay: float) -> ProbeResult:
    key = entry_key(entry)
    statuses: list[tuple[str, str, float]] = []

    for attempt in range(1, attempts + 1):
        status, detail, elapsed = run_one_probe(entry, timeout)
        statuses.append((status, detail, elapsed))

        # A successful, restricted, or deliberately untested result is decisive.
        if status in {"working", "access_restricted", "untested"}:
            break
        if attempt < attempts:
            time.sleep(retry_delay)

    elapsed_total = sum(item[2] for item in statuses)
    final_status, final_detail, _ = statuses[-1]

    # Only call an endpoint dead within one run when every attempt returned a
    # hard not-found/gone signal. Even then, history is required before removal.
    if final_status == "dead" and any(item[0] != "dead" for item in statuses):
        final_status = "temporary_failed"
        final_detail = "mixed probe failures; retained"

    return ProbeResult(
        key=key,
        name=entry.name,
        tvg_id=entry.tvg_id,
        url=entry.url,
        status=final_status,
        detail=final_detail,
        attempts=len(statuses),
        elapsed_seconds=round(elapsed_total, 2),
    )


def load_previous_state(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(data, dict) and isinstance(data.get("streams"), dict):
        return data["streams"]
    return {}


def apply_history(
    result: ProbeResult,
    previous: dict[str, dict],
    drop_after: int,
) -> ProbeResult:
    old = previous.get(result.key, {})
    old_failures = int(old.get("consecutive_failures", 0) or 0)

    if result.status == "working":
        result.consecutive_failures = 0
    elif result.status in {"access_restricted", "untested"}:
        # A retained/non-dead result breaks the consecutive-failure streak.
        result.consecutive_failures = 0
    else:
        result.consecutive_failures = old_failures + 1

    # Never remove a stream after one validation run, even for a hard 404/410.
    # Public IPTV endpoints can be briefly stale, rotated or rate-limited.
    result.drop = (
        result.status in {"dead", "temporary_failed"}
        and result.consecutive_failures >= drop_after
    )
    return result


def write_clean_playlist(header: str, entries: Iterable[Entry], dropped_keys: set[str], path: Path) -> None:
    output = [header]
    for entry in entries:
        if entry_key(entry) in dropped_keys:
            continue
        output.extend(entry.lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="M3U file path or URL")
    parser.add_argument("--workers", type=int, default=min(24, (os.cpu_count() or 4) * 4))
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--retry-delay", type=float, default=1.5)
    parser.add_argument("--drop-after", type=int, default=3, help="consecutive failed validation runs before removal")
    parser.add_argument("--state", default="output/stream-health.json")
    parser.add_argument("--cleaned", default="output/english-validated.m3u")
    parser.add_argument("--report", default="output/stream-health-summary.json")
    args = parser.parse_args()

    if shutil.which("ffprobe") is None:
        print("ffprobe was not found. Install FFmpeg and ensure ffprobe is on PATH.", file=sys.stderr)
        return 2

    header, entries = parse_playlist(load_text(args.source))
    previous = load_previous_state(Path(args.state))

    print(f"Checking {len(entries)} streams with {args.workers} workers...")
    results: list[ProbeResult] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {
            executor.submit(probe_entry, entry, args.timeout, args.attempts, args.retry_delay): entry
            for entry in entries
        }
        completed = 0
        for future in concurrent.futures.as_completed(future_map):
            entry = future_map[future]
            completed += 1
            try:
                result = future.result()
            except Exception as exc:
                result = ProbeResult(
                    key=entry_key(entry),
                    name=entry.name,
                    tvg_id=entry.tvg_id,
                    url=entry.url,
                    status="temporary_failed",
                    detail=f"validator error: {exc}",
                    attempts=0,
                    elapsed_seconds=0.0,
                )
            results.append(apply_history(result, previous, args.drop_after))
            if completed % 50 == 0 or completed == len(entries):
                print(f"  {completed}/{len(entries)} checked")

    results.sort(key=lambda item: (item.name.casefold(), item.url))
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()

    streams = {
        result.key: {
            **asdict(result),
            "last_checked": timestamp,
        }
        for result in results
    }
    state_doc = {"generated_at": timestamp, "streams": streams}

    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    dropped = {result.key for result in results if result.drop}

    state_path = Path(args.state)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state_doc, indent=2) + "\n", encoding="utf-8")

    write_clean_playlist(header, entries, dropped, Path(args.cleaned))

    summary = {
        "generated_at": timestamp,
        "source": args.source,
        "streams_checked": len(results),
        "status_counts": counts,
        "streams_removed_from_cleaned_playlist": len(dropped),
        "drop_after_consecutive_failures": args.drop_after,
        "attempts_per_run": args.attempts,
        "timeout_seconds": args.timeout,
        "note": "all removals require repeated failed validation runs; working, access_restricted and untested results reset the failure streak",
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
