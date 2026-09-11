#!/usr/bin/env python3
"""Run iptv-org/epg over a channels file in resilient, memory-safe batches.

A failed multi-channel batch is retried channel-by-channel.  This keeps one bad
provider from discarding unrelated guide data and makes the same behaviour
reusable for primary and alternate-source EPG passes.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


def clone_element(element: ET.Element) -> ET.Element:
    return ET.fromstring(ET.tostring(element, encoding="utf-8"))


def split_channels(input_path: Path, output_dir: Path, size: int) -> list[Path]:
    if size < 1:
        raise ValueError("chunk size must be at least 1")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    root = ET.parse(input_path).getroot()
    channels = list(root.findall("channel"))
    files: list[Path] = []
    for index, start in enumerate(range(0, len(channels), size), start=1):
        chunk_root = ET.Element("channels")
        for channel in channels[start : start + size]:
            chunk_root.append(clone_element(channel))
        path = output_dir / f"chunk-{index:03d}.channels.xml"
        tree = ET.ElementTree(chunk_root)
        ET.indent(tree, space="  ")
        tree.write(path, encoding="utf-8", xml_declaration=True)
        files.append(path)
    return files


def channel_count(path: Path) -> int:
    return len(ET.parse(path).getroot().findall("channel"))


def run_grab(
    epg_root: Path,
    channels: Path,
    output: Path,
    days: int,
    max_connections: int,
    timeout_ms: int,
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "npm",
        "run",
        "grab",
        "--",
        f"--channels={channels}",
        f"--output={output}",
        f"--days={days}",
        f"--maxConnections={max_connections}",
        f"--timeout={timeout_ms}",
    ]
    print("$", " ".join(str(part) for part in command), flush=True)
    result = subprocess.run(command, cwd=epg_root, env=os.environ.copy(), check=False)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channels", required=True)
    parser.add_argument("--epg-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--failures", required=True)
    parser.add_argument("--label", default="epg")
    parser.add_argument("--chunk-size", type=int, default=20)
    parser.add_argument("--days", type=int, default=2)
    parser.add_argument("--max-connections", type=int, default=4)
    parser.add_argument("--retry-connections", type=int, default=2)
    parser.add_argument("--timeout-ms", type=int, default=20000)
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args()

    channels_path = Path(args.channels).resolve()
    epg_root = Path(args.epg_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    work_dir = Path(args.work_dir).resolve()
    summary_path = Path(args.summary).resolve()
    failures_path = Path(args.failures).resolve()

    requested_channels = channel_count(channels_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    failures_path.parent.mkdir(parents=True, exist_ok=True)
    failures_path.write_text("", encoding="utf-8")

    if requested_channels == 0:
        summary = {
            "label": args.label,
            "requested_channels": 0,
            "chunk_size": args.chunk_size,
            "successful_primary_chunks": 0,
            "failed_primary_chunks": 0,
            "successful_retry_channels": 0,
            "failed_retry_channels": 0,
            "fragments_generated": 0,
        }
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 0

    chunk_dir = work_dir / "chunks"
    retry_root = work_dir / "retry"
    chunks = split_channels(channels_path, chunk_dir, args.chunk_size)
    if retry_root.exists():
        shutil.rmtree(retry_root)
    retry_root.mkdir(parents=True, exist_ok=True)

    # Avoid accidentally merging stale files from a previous local run.
    for stale in output_dir.glob("*.xml"):
        stale.unlink()

    primary_success = 0
    primary_failed = 0
    retry_success = 0
    retry_failed = 0
    fragment_count = 0

    for channels in chunks:
        chunk = channels.stem.replace(".channels", "")
        output = output_dir / f"{chunk}.xml"
        print(f"=== {args.label}: {chunk} ===", flush=True)
        status = run_grab(
            epg_root,
            channels.resolve(),
            output.resolve(),
            args.days,
            args.max_connections,
            args.timeout_ms,
        )
        if status == 0 and output.exists() and output.stat().st_size > 0:
            primary_success += 1
            fragment_count += 1
            continue

        primary_failed += 1
        output.unlink(missing_ok=True)
        print(f"{chunk} failed as a batch; retrying each channel separately", flush=True)
        retry_dir = retry_root / chunk
        retry_chunks = split_channels(channels, retry_dir, 1)

        for retry_channels in retry_chunks:
            retry_name = retry_channels.stem.replace(".channels", "")
            retry_output = output_dir / f"{chunk}-{retry_name}.xml"
            status = run_grab(
                epg_root,
                retry_channels.resolve(),
                retry_output.resolve(),
                args.days,
                args.retry_connections,
                args.timeout_ms,
            )
            if status == 0 and retry_output.exists() and retry_output.stat().st_size > 0:
                retry_success += 1
                fragment_count += 1
            else:
                retry_failed += 1
                retry_output.unlink(missing_ok=True)
                with failures_path.open("a", encoding="utf-8") as handle:
                    handle.write(f"{chunk}/{retry_name}\texit={status}\n")

    summary = {
        "label": args.label,
        "requested_channels": requested_channels,
        "chunk_size": args.chunk_size,
        "successful_primary_chunks": primary_success,
        "failed_primary_chunks": primary_failed,
        "successful_retry_channels": retry_success,
        "failed_retry_channels": retry_failed,
        "fragments_generated": fragment_count,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))

    if fragment_count == 0 and not args.allow_empty:
        print("No EPG fragments were generated successfully.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
