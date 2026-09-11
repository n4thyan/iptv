import gzip
import importlib.util
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_epg_from_feeds.py"
spec = importlib.util.spec_from_file_location("build_epg_from_feeds", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class FastEpgBuilderTests(unittest.TestCase):
    def test_parse_source_keeps_only_requested_ids_and_deduplicates_programmes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.xml.gz"
            xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="BBCOne.uk"><display-name>BBC One</display-name></channel>
  <channel id="Other.us"><display-name>Other</display-name></channel>
  <programme start="20260911120000 +0000" stop="20260911130000 +0000" channel="BBCOne.uk"><title>News</title></programme>
  <programme start="20260911120000 +0000" stop="20260911130000 +0000" channel="BBCOne.uk"><title>News</title></programme>
  <programme start="20260911120000 +0000" stop="20260911130000 +0000" channel="Other.us"><title>Other</title></programme>
</tv>'''
            with gzip.open(source, "wb") as handle:
                handle.write(xml)

            channels = {}
            programmes = []
            seen = set()
            programmed = set()
            stats = mod.parse_source(
                source,
                {"BBCOne.uk"},
                channels,
                programmes,
                seen,
                programmed,
            )

            self.assertEqual(stats["channels"], 1)
            self.assertEqual(stats["programmes"], 1)
            self.assertEqual(programmed, {"BBCOne.uk"})
            self.assertEqual(len(programmes), 1)
            self.assertIn("BBCOne.uk", channels)

    def test_write_guide_only_outputs_programmed_channels(self):
        with tempfile.TemporaryDirectory() as tmp:
            bbc = ET.Element("channel", {"id": "BBCOne.uk"})
            ET.SubElement(bbc, "display-name").text = "BBC One"
            unused = ET.Element("channel", {"id": "Unused.uk"})
            programme = ET.Element(
                "programme",
                {
                    "channel": "BBCOne.uk",
                    "start": "20260911120000 +0000",
                    "stop": "20260911130000 +0000",
                },
            )
            ET.SubElement(programme, "title").text = "News"

            output = Path(tmp) / "guide.xml"
            mod.write_guide(
                output,
                {"BBCOne.uk": bbc, "Unused.uk": unused},
                [programme],
                {"BBCOne.uk"},
            )
            root = ET.parse(output).getroot()
            self.assertEqual(
                [item.attrib["id"] for item in root.findall("channel")],
                ["BBCOne.uk"],
            )
            self.assertEqual(len(root.findall("programme")), 1)


if __name__ == "__main__":
    unittest.main()
