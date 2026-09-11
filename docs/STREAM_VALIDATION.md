# Stream validation

## Why this runs on the PC, not GitHub Actions

A public IPTV stream can work in the UK but fail from a GitHub-hosted runner in another region. Automatically deleting streams based on a cloud runner would therefore create false positives, especially for geo-restricted channels.

Use `tools/validate_streams.py` manually from the PC when a cleanup pass is wanted. The PC does **not** need to stay on afterwards.

## Requirements

- Python 3.10+
- FFmpeg installed with `ffprobe` available on `PATH`

On Windows, confirm this first:

```powershell
ffprobe -version
```

## Recommended first run

From the repository root:

```powershell
python tools/validate_streams.py https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u
```

Defaults are intentionally conservative:

- up to 24 parallel probes,
- 8 second ffprobe timeout,
- 2 attempts per stream,
- **all** failed streams need 3 consecutive validation runs before removal, including repeated HTTP 404/410 results,
- a working, access-restricted or deliberately untested result resets that failure streak,
- HTTP 401/403/451 and similar access/geo restrictions are kept,
- Kodi web-scraper entries are kept because ffprobe cannot test them directly.

A 404/410 is still recorded as a stronger `dead` signal than an ordinary timeout, but it is not enough on its own to delete a stream after one run. This protects against temporarily stale endpoints, CDN changes and short-lived upstream failures.

## Outputs

The tool writes:

- `output/stream-health.json` — persistent per-stream history,
- `output/stream-health-summary.json` — counts/status summary,
- `output/english-validated.m3u` — cleaned playlist containing only streams that have not met the removal threshold.

Keep `stream-health.json` between cleanup runs so temporary failures do not immediately remove channels.

## Faster or slower runs

Example with 32 workers and a 6 second probe timeout:

```powershell
python tools/validate_streams.py https://raw.githubusercontent.com/n4thyan/iptv/generated/english.m3u --workers 32 --timeout 6
```

If a network is being hammered or streams start rate-limiting, reduce `--workers` rather than increasing it.

## Publishing a validated playlist

For now the validator deliberately does **not** auto-push its result. That gives us a chance to inspect its summary before replacing the generated playlist. Once it has been tested on the user's UK connection, the workflow can be extended to accept the validated dead-stream state without requiring the PC to remain online.
