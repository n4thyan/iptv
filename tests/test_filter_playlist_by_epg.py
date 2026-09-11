import importlib.util
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "filter_playlist_by_epg.py"
spec = importlib.util.spec_from_file_location("filter_playlist_by_epg", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class CuratedPlaylistTests(unittest.TestCase):
    def test_filter_playlist_keeps_only_channels_with_programmes(self):
        source = '''#EXTM3U x-tvg-url="https://example.invalid/guide.xml.gz"
#EXTINF:-1 tvg-id="BBCOne.uk" group-title="UK",BBC One
https://example.invalid/bbc.m3u8
#EXTINF:-1 tvg-id="Blank.us" group-title="News",Blank
#KODIPROP:inputstream=inputstream.adaptive
https://example.invalid/blank.m3u8
'''
        filtered, stats = mod.filter_playlist_text(source, {"BBCOne.uk"})
        self.assertIn('tvg-id="BBCOne.uk"', filtered)
        self.assertNotIn('tvg-id="Blank.us"', filtered)
        self.assertEqual(stats["entries_total"], 2)
        self.assertEqual(stats["entries_kept"], 1)
        self.assertEqual(stats["entries_without_programme_data"], 1)

    def test_programme_channel_ids_reads_xmltv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = ET.Element("tv")
            ET.SubElement(root, "channel", {"id": "BBCOne.uk"})
            ET.SubElement(
                root,
                "programme",
                {
                    "channel": "BBCOne.uk",
                    "start": "20260911120000 +0000",
                    "stop": "20260911130000 +0000",
                },
            )
            path = Path(tmp) / "guide.xml"
            ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
            self.assertEqual(mod.programme_channel_ids(path), {"BBCOne.uk"})


if __name__ == "__main__":
    unittest.main()
