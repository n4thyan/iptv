import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


split_mod = load_module("split_epg_channels", ROOT / "scripts" / "split_epg_channels.py")
merge_mod = load_module("merge_xmltv", ROOT / "scripts" / "merge_xmltv.py")


class EpgChunkingTests(unittest.TestCase):
    def test_split_epg_channels_creates_expected_chunks_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "channels.xml"
            output_dir = root / "chunks"
            manifest_path = root / "manifest.json"

            channels = ET.Element("channels")
            for index in range(5):
                channel = ET.SubElement(
                    channels,
                    "channel",
                    {
                        "site": "example.com",
                        "lang": "en",
                        "xmltv_id": f"Channel{index}.uk",
                        "site_id": str(index),
                    },
                )
                channel.text = f"Channel {index}"
            ET.ElementTree(channels).write(input_path, encoding="utf-8", xml_declaration=True)

            output_dir.mkdir()
            stale = output_dir / "chunk-999.channels.xml"
            stale.write_text("stale", encoding="utf-8")

            argv = [
                "split_epg_channels.py",
                "--input",
                str(input_path),
                "--output-dir",
                str(output_dir),
                "--size",
                "2",
                "--manifest",
                str(manifest_path),
            ]
            with patch.object(sys, "argv", argv):
                self.assertEqual(split_mod.main(), 0)

            chunks = sorted(output_dir.glob("chunk-*.channels.xml"))
            self.assertEqual([path.name for path in chunks], [
                "chunk-001.channels.xml",
                "chunk-002.channels.xml",
                "chunk-003.channels.xml",
            ])
            self.assertFalse(stale.exists())
            self.assertEqual(
                [len(ET.parse(path).getroot().findall("channel")) for path in chunks],
                [2, 2, 1],
            )

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["channels"], 5)
            self.assertEqual(manifest["chunk_size"], 2)
            self.assertEqual(manifest["chunk_count"], 3)

    def test_merge_xmltv_deduplicates_channel_definitions_and_keeps_programmes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "chunk-001.xml"
            second = root / "chunk-002.xml"
            output = root / "guide.xml"

            first.write_text(
                """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<tv generator-info-name=\"test\">
  <channel id=\"One.uk\"><display-name>One</display-name></channel>
  <programme channel=\"One.uk\" start=\"20260911080000 +0000\" stop=\"20260911090000 +0000\"><title>Morning</title></programme>
</tv>
""",
                encoding="utf-8",
            )
            second.write_text(
                """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<tv generator-info-name=\"test\">
  <channel id=\"One.uk\"><display-name>One duplicate</display-name></channel>
  <channel id=\"Two.uk\"><display-name>Two</display-name></channel>
  <programme channel=\"Two.uk\" start=\"20260911090000 +0000\" stop=\"20260911100000 +0000\"><title>News</title></programme>
</tv>
""",
                encoding="utf-8",
            )

            argv = [
                "merge_xmltv.py",
                str(root / "chunk-*.xml"),
                "--output",
                str(output),
            ]
            with patch.object(sys, "argv", argv):
                self.assertEqual(merge_mod.main(), 0)

            merged = ET.parse(output).getroot()
            self.assertEqual(merged.tag, "tv")
            self.assertEqual(merged.attrib.get("generator-info-name"), "test")
            self.assertEqual(
                {channel.attrib["id"] for channel in merged.findall("channel")},
                {"One.uk", "Two.uk"},
            )
            self.assertEqual(len(merged.findall("channel")), 2)
            self.assertEqual(len(merged.findall("programme")), 2)
            self.assertEqual(
                {programme.attrib["channel"] for programme in merged.findall("programme")},
                {"One.uk", "Two.uk"},
            )


if __name__ == "__main__":
    unittest.main()
