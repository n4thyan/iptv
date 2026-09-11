import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "validate_streams.py"
spec = importlib.util.spec_from_file_location("validate_streams", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class StreamValidatorTests(unittest.TestCase):
    def test_playlist_parser_preserves_kodi_directives(self):
        text = """#EXTM3U x-tvg-url=\"guide.xml.gz\"
#EXTINF:-1 tvg-id=\"Example.uk\",Example
#EXTVLCOPT:http-referrer=https://example.com/
#KODIPROP:inputstream=inputstream.adaptive
https://cdn.example.com/live.m3u8
"""
        header, entries = mod.parse_playlist(text)
        self.assertIn("x-tvg-url", header)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].tvg_id, "Example.uk")
        self.assertEqual(entries[0].lines[1], "#EXTVLCOPT:http-referrer=https://example.com/")
        self.assertEqual(entries[0].lines[2], "#KODIPROP:inputstream=inputstream.adaptive")

    def test_access_restriction_is_not_classed_as_dead(self):
        status, detail = mod.classify_failure("Server returned 403 Forbidden", False)
        self.assertEqual(status, "access_restricted")
        self.assertIn("403", detail)

    def test_not_found_is_hard_dead_signal(self):
        status, detail = mod.classify_failure("Server returned 404 Not Found", False)
        self.assertEqual(status, "dead")
        self.assertIn("404", detail)

    def test_timeout_is_temporary(self):
        status, _ = mod.classify_failure("", True)
        self.assertEqual(status, "temporary_failed")

    def test_transient_failure_requires_history_before_drop(self):
        result = mod.ProbeResult(
            key="Example.uk\thttps://example.com/live.m3u8",
            name="Example",
            tvg_id="Example.uk",
            url="https://example.com/live.m3u8",
            status="temporary_failed",
            detail="timeout",
            attempts=2,
            elapsed_seconds=16.0,
        )
        previous = {result.key: {"consecutive_failures": 1}}
        mod.apply_history(result, previous, drop_after=3)
        self.assertEqual(result.consecutive_failures, 2)
        self.assertFalse(result.drop)

        result2 = mod.ProbeResult(
            key=result.key,
            name=result.name,
            tvg_id=result.tvg_id,
            url=result.url,
            status="temporary_failed",
            detail="timeout",
            attempts=2,
            elapsed_seconds=16.0,
        )
        previous2 = {result.key: {"consecutive_failures": 2}}
        mod.apply_history(result2, previous2, drop_after=3)
        self.assertTrue(result2.drop)

    def test_hard_404_also_requires_history_before_drop(self):
        result = mod.ProbeResult(
            key="Example.uk\thttps://example.com/missing.m3u8",
            name="Example",
            tvg_id="Example.uk",
            url="https://example.com/missing.m3u8",
            status="dead",
            detail="HTTP 404",
            attempts=2,
            elapsed_seconds=2.0,
        )
        previous = {result.key: {"consecutive_failures": 1}}
        mod.apply_history(result, previous, drop_after=3)
        self.assertEqual(result.consecutive_failures, 2)
        self.assertFalse(result.drop)

        result2 = mod.ProbeResult(
            key=result.key,
            name=result.name,
            tvg_id=result.tvg_id,
            url=result.url,
            status="dead",
            detail="HTTP 404",
            attempts=2,
            elapsed_seconds=2.0,
        )
        previous2 = {result.key: {"consecutive_failures": 2}}
        mod.apply_history(result2, previous2, drop_after=3)
        self.assertEqual(result2.consecutive_failures, 3)
        self.assertTrue(result2.drop)

    def test_access_restriction_breaks_failure_streak(self):
        result = mod.ProbeResult(
            key="Example.uk\thttps://example.com/live.m3u8",
            name="Example",
            tvg_id="Example.uk",
            url="https://example.com/live.m3u8",
            status="access_restricted",
            detail="HTTP 403",
            attempts=1,
            elapsed_seconds=1.0,
        )
        previous = {result.key: {"consecutive_failures": 2}}
        mod.apply_history(result, previous, drop_after=3)
        self.assertEqual(result.consecutive_failures, 0)
        self.assertFalse(result.drop)

    def test_untested_scraper_entry_breaks_failure_streak(self):
        result = mod.ProbeResult(
            key="Example.uk\t@plugin-entry",
            name="Example",
            tvg_id="Example.uk",
            url="@plugin-entry",
            status="untested",
            detail="Kodi web-scraper entry",
            attempts=1,
            elapsed_seconds=0.0,
        )
        previous = {result.key: {"consecutive_failures": 2}}
        mod.apply_history(result, previous, drop_after=3)
        self.assertEqual(result.consecutive_failures, 0)
        self.assertFalse(result.drop)


if __name__ == "__main__":
    unittest.main()
