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
    def test_compatibility_bridge_rewrites_dotted_hd_id_to_playlist_variants(self):
        requested = {"Channel4.uk@UK", "Channel4.uk@UKHD"}
        index = mod.build_target_index(requested)
        targets, mode = mod.targets_for_source_id("Channel.4.HD.uk", requested, index)
        self.assertEqual(mode, "compatible")
        self.assertEqual(targets, ["Channel4.uk@UK", "Channel4.uk@UKHD"])

    def test_compatibility_bridge_is_country_aware(self):
        requested = {"Channel4.uk@UK"}
        index = mod.build_target_index(requested)
        targets, mode = mod.targets_for_source_id("Channel.4.HD.us", requested, index)
        self.assertEqual(mode, "unmatched")
        self.assertEqual(targets, [])

    def test_us2_dataset_suffix_maps_to_us_playlist_namespace(self):
        requested = {"BBCNews.us", "CNBC.us"}
        index = mod.build_target_index(requested)
        targets, mode = mod.targets_for_source_id("CNBC.HD.us2", requested, index)
        self.assertEqual(mode, "compatible")
        self.assertEqual(targets, ["CNBC.us"])

    def test_us_special_dataset_suffixes_map_to_us_country_only(self):
        requested = {"KABCDT1.us", "ESPN.us"}
        index = mod.build_target_index(requested)
        self.assertEqual(mod.split_country_id("KABCDT1.us_locals1")[1], "us")
        self.assertEqual(mod.split_country_id("ESPN.HD.us_sports1")[1], "us")
        self.assertEqual(mod.split_country_id("ESPN.HD.uk")[1], "uk")

    def test_regional_bbc_one_london_maps_to_london_playlist_variants(self):
        requested = {
            "BBCOne.uk@London",
            "BBCOne.uk@LondonHD",
            "BBCOne.uk@East",
            "BBCOne.uk@NorthernIreland",
        }
        index = mod.build_target_index(requested)
        targets, mode = mod.targets_for_source_id("BBC.One.Lon.HD.uk", requested, index)
        self.assertEqual(mode, "compatible")
        self.assertEqual(targets, ["BBCOne.uk@London", "BBCOne.uk@LondonHD"])

    def test_regional_bbc_one_ni_maps_without_cross_region_leakage(self):
        requested = {
            "BBCOne.uk@London",
            "BBCOne.uk@NorthernIreland",
            "BBCOne.uk@NorthernIrelandHD",
            "BBCOne.uk@Scotland",
        }
        index = mod.build_target_index(requested)
        targets, mode = mod.targets_for_source_id("BBC.One.NI.HD.uk", requested, index)
        self.assertEqual(mode, "compatible")
        self.assertEqual(
            targets,
            ["BBCOne.uk@NorthernIreland", "BBCOne.uk@NorthernIrelandHD"],
        )

    def test_regional_bbc_one_yorks_abbreviation_maps_to_yorkshire(self):
        requested = {"BBCOne.uk@Yorkshire", "BBCOne.uk@YorkshireHD"}
        index = mod.build_target_index(requested)
        targets, mode = mod.targets_for_source_id("BBC.One.Yorks.HD.uk", requested, index)
        self.assertEqual(mode, "compatible")
        self.assertEqual(targets, ["BBCOne.uk@Yorkshire", "BBCOne.uk@YorkshireHD"])

    def test_parse_source_preserves_metadata_and_deduplicates_programmes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.xml.gz"
            xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="Channel.4.HD.uk"><display-name>Channel 4 HD</display-name></channel>
  <channel id="Other.us"><display-name>Other</display-name></channel>
  <programme start="20260911120000 +0000" stop="20260911130000 +0000" channel="Channel.4.HD.uk"><title>News</title><desc>Latest headlines.</desc></programme>
  <programme start="20260911120000 +0000" stop="20260911130000 +0000" channel="Channel.4.HD.uk"><title>News</title><desc>Latest headlines.</desc></programme>
  <programme start="20260911120000 +0000" stop="20260911130000 +0000" channel="Other.us"><title>Other</title></programme>
</tv>'''
            with gzip.open(source, "wb") as handle:
                handle.write(xml)

            requested = {"Channel4.uk@UKHD"}
            channels = {}
            programmes = []
            seen = set()
            programmed = set()
            stats = mod.parse_source(
                source,
                requested,
                mod.build_target_index(requested),
                channels,
                programmes,
                seen,
                programmed,
            )

            self.assertEqual(stats["channels"], 1)
            self.assertEqual(stats["programmes"], 1)
            self.assertEqual(stats["compatible_source_ids"], 1)
            self.assertEqual(programmed, {"Channel4.uk@UKHD"})
            self.assertEqual(len(programmes), 1)
            self.assertIn("Channel4.uk@UKHD", channels)
            self.assertEqual(channels["Channel4.uk@UKHD"].attrib["id"], "Channel4.uk@UKHD")
            self.assertEqual(channels["Channel4.uk@UKHD"].findtext("display-name"), "Channel 4 HD")
            self.assertEqual(programmes[0].attrib["channel"], "Channel4.uk@UKHD")
            self.assertEqual(programmes[0].findtext("title"), "News")
            self.assertEqual(programmes[0].findtext("desc"), "Latest headlines.")

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
