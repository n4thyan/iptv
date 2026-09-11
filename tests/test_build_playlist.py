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

    def test_extract_tvg_ids_ignores_non_channel_lines(self):
        text = """#EXTM3U
#EXTINF:-1 tvg-id="BBCOne.uk@London" group-title="General",BBC One
https://example.com/bbc.m3u8
#EXTVLCOPT:http-user-agent=Kodi
#EXTINF:-1 tvg-id="ITV1.uk@London",ITV1
https://example.com/itv.m3u8
"""
        self.assertEqual(
            mod.extract_tvg_ids(text),
            {"BBCOne.uk@London", "ITV1.uk@London"},
        )

    def test_extra_group_spec_requires_name_and_source(self):
        self.assertEqual(
            mod.parse_extra_group_spec("UK=https://example.com/uk.m3u"),
            ("UK", "https://example.com/uk.m3u"),
        )
        with self.assertRaises(Exception):
            mod.parse_extra_group_spec("UK")
        with self.assertRaises(Exception):
            mod.parse_extra_group_spec("=https://example.com/uk.m3u")

    def test_add_group_appends_without_rebuilding_extinf(self):
        line = (
            '#EXTINF:-1 tvg-id="BBCOne.uk@London" tvg-logo="https://example/logo.png" '
            'group-title="General;Entertainment",BBC One London'
        )
        self.assertEqual(
            mod.add_group_to_extinf(line, "UK"),
            (
                '#EXTINF:-1 tvg-id="BBCOne.uk@London" tvg-logo="https://example/logo.png" '
                'group-title="General;Entertainment;UK",BBC One London'
            ),
        )

    def test_add_group_is_idempotent_case_insensitively(self):
        line = '#EXTINF:-1 tvg-id="BBCOne.uk" group-title="General;UK",BBC One'
        self.assertEqual(mod.add_group_to_extinf(line, "uk"), line)

    def test_add_group_inserts_group_title_when_missing(self):
        line = '#EXTINF:-1 tvg-id="BBCOne.uk" tvg-logo="https://example/logo.png",BBC One'
        self.assertEqual(
            mod.add_group_to_extinf(line, "UK"),
            (
                '#EXTINF:-1 tvg-id="BBCOne.uk" tvg-logo="https://example/logo.png" '
                'group-title="UK",BBC One'
            ),
        )

    def test_add_group_handles_commas_inside_quoted_metadata(self):
        line = (
            '#EXTINF:-1 tvg-id="BBCOne.uk" tvg-logo="https://example/logo,small.png",'
            'BBC One'
        )
        self.assertEqual(
            mod.add_group_to_extinf(line, "UK"),
            (
                '#EXTINF:-1 tvg-id="BBCOne.uk" tvg-logo="https://example/logo,small.png" '
                'group-title="UK",BBC One'
            ),
        )


if __name__ == "__main__":
    unittest.main()
