import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_epg_fallback_channels.py"
spec = importlib.util.spec_from_file_location("build_epg_fallback_channels", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class EpgFallbackTests(unittest.TestCase):
    def test_channels_with_programmes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "guide.xml"
            path.write_text(
                "<?xml version='1.0'?><tv>"
                "<channel id='A.uk'/><channel id='B.uk'/>"
                "<programme channel='A.uk' start='20260101000000 +0000'/>"
                "</tv>",
                encoding="utf-8",
            )
            self.assertEqual(mod.channels_with_programmes(path), {"A.uk"})

    def test_build_channel_rewrites_target_id(self):
        source = {
            "site": "example.com",
            "site_id": "bbc1",
            "lang": "en",
            "name": "BBC One",
        }
        channel = mod.build_channel("BBCOne.uk", source)
        self.assertEqual(channel.attrib["xmltv_id"], "BBCOne.uk")
        self.assertEqual(channel.attrib["site_id"], "bbc1")
        self.assertEqual(channel.text, "BBC One")


if __name__ == "__main__":
    unittest.main()
