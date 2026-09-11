import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "xmltv_stats.py"
spec = importlib.util.spec_from_file_location("xmltv_stats", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class XmltvStatsTests(unittest.TestCase):
    def test_collect_stats_counts_guide_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            guide = Path(tmp) / "guide.xml"
            guide.write_text(
                """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<tv>
  <channel id=\"One.uk\"><display-name>One</display-name></channel>
  <channel id=\"Two.uk\"><display-name>Two</display-name></channel>
  <programme channel=\"One.uk\" start=\"20260911080000 +0000\" stop=\"20260911090000 +0000\"><title>A</title></programme>
  <programme channel=\"One.uk\" start=\"20260911090000 +0000\" stop=\"20260911100000 +0000\"><title>B</title></programme>
  <programme channel=\"Missing.uk\" start=\"20260911100000 +0000\" stop=\"20260911110000 +0000\"><title>C</title></programme>
</tv>
""",
                encoding="utf-8",
            )

            stats = mod.collect_stats(guide)
            self.assertEqual(stats["channel_elements"], 2)
            self.assertEqual(stats["unique_channel_ids"], 2)
            self.assertEqual(stats["programme_elements"], 3)
            self.assertEqual(stats["channels_with_programmes"], 2)
            self.assertEqual(stats["programmes_without_channel"], 0)
            self.assertEqual(stats["programme_channels_missing_definition"], 1)
            self.assertGreater(stats["guide_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
