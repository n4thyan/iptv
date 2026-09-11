import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_playlist.py"
spec = importlib.util.spec_from_file_location("build_playlist", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class PlaylistBuilderTests(unittest.TestCase):
    def test_preserves_directives_before_stream_url(self):
        lines = [
            '#EXTINF:-1 tvg-id="Example.uk",Example',
            '#EXTVLCOPT:http-referrer=https://example.com/',
            '#KODIPROP:inputstream=inputstream.adaptive',
            'https://cdn.example.com/live.m3u8',
            '#EXTINF:-1 tvg-id="Next.uk",Next',
            'https://cdn.example.com/next.m3u8',
        ]
        stanza, next_index = mod.read_stanza(lines, 0)
        self.assertEqual(
            stanza,
            [
                lines[0],
                lines[1],
                lines[2],
                lines[3],
            ],
        )
        self.assertEqual(next_index, 4)

    def test_malformed_stanza_does_not_consume_next_channel(self):
        lines = [
            '#EXTINF:-1 tvg-id="Broken.uk",Broken',
            '#EXTVLCOPT:http-referrer=https://example.com/',
            '#EXTINF:-1 tvg-id="Good.uk",Good',
            'https://cdn.example.com/good.m3u8',
        ]
        stanza, next_index = mod.read_stanza(lines, 0)
        self.assertIsNone(stanza)
        self.assertEqual(next_index, 2)

    def test_database_channel_id_strips_feed_suffix(self):
        self.assertEqual(mod.base_channel_id("BBCOne.uk@London"), "BBCOne.uk")

    def test_adult_swim_is_not_removed_by_name_fallback(self):
        attrs = {"group-title": "Entertainment"}
        self.assertFalse(mod.adult_by_fallback(attrs, "Adult Swim"))

    def test_explicit_adult_group_is_removed(self):
        attrs = {"group-title": "XXX"}
        self.assertTrue(mod.adult_by_fallback(attrs, "Example TV"))


if __name__ == "__main__":
    unittest.main()
