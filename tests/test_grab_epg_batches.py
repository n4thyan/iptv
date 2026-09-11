import importlib.util
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "grab_epg_batches.py"
spec = importlib.util.spec_from_file_location("grab_epg_batches", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class GrabEpgBatchTests(unittest.TestCase):
    def test_split_channels_preserves_every_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = ET.Element("channels")
            for index in range(5):
                channel = ET.SubElement(
                    root,
                    "channel",
                    {
                        "site": "example.com",
                        "site_id": str(index),
                        "lang": "en",
                        "xmltv_id": f"Channel{index}.uk",
                    },
                )
                channel.text = f"Channel {index}"
            source = Path(tmp) / "channels.xml"
            ET.ElementTree(root).write(source, encoding="utf-8", xml_declaration=True)

            output = Path(tmp) / "chunks"
            files = mod.split_channels(source, output, 2)
            self.assertEqual(len(files), 3)
            counts = [mod.channel_count(path) for path in files]
            self.assertEqual(counts, [2, 2, 1])
            ids = []
            for path in files:
                ids.extend(
                    channel.attrib["xmltv_id"]
                    for channel in ET.parse(path).getroot().findall("channel")
                )
            self.assertEqual(ids, [f"Channel{i}.uk" for i in range(5)])


if __name__ == "__main__":
    unittest.main()
