import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_channel_catalog.py"
spec = importlib.util.spec_from_file_location("build_channel_catalog", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class ChannelCatalogTests(unittest.TestCase):
    def test_base_id_removes_feed_suffix(self):
        self.assertEqual(mod.base_id("BBCOne.uk@London"), "BBCOne.uk")
        self.assertEqual(mod.base_id("BBCOne.uk"), "BBCOne.uk")

    def test_playlist_entries_extract_exact_tvg_id_and_name(self):
        text = """#EXTM3U
#EXTINF:-1 tvg-id=\"BBCOne.uk@London\" group-title=\"General\",BBC One London
https://example.com/one.m3u8
#EXTINF:-1 tvg-id=\"BBCNews.uk\",BBC News
https://example.com/news.m3u8
"""
        entries = mod.playlist_entries(text)
        self.assertEqual(entries["BBCOne.uk@London"], "BBC One London")
        self.assertEqual(entries["BBCNews.uk"], "BBC News")

    def test_clean_string_list_ignores_empty_values(self):
        self.assertEqual(mod.clean_string_list(["BBC1", "", "  BBC One  "]), ["BBC1", "BBC One"])
        self.assertEqual(mod.clean_string_list(None), [])


if __name__ == "__main__":
    unittest.main()
