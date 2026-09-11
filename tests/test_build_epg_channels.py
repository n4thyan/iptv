import importlib.util
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_epg_channels.py"
spec = importlib.util.spec_from_file_location("build_epg_channels", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class EpgMapperTests(unittest.TestCase):
    def make_candidate(self, xmltv_id: str, lang: str = "en", site: str = "example.com"):
        channel = ET.Element(
            "channel",
            {
                "site": site,
                "lang": lang,
                "xmltv_id": xmltv_id,
                "site_id": "1",
            },
        )
        channel.text = "Example"
        return mod.Candidate(channel=channel, path=Path(f"sites/{site}/channels.xml"), source_xmltv_id=xmltv_id)

    def test_base_id(self):
        self.assertEqual(mod.base_id("BBCOne.uk@London"), "BBCOne.uk")
        self.assertEqual(mod.base_id("BBCOne.uk"), "BBCOne.uk")

    def test_exact_match_beats_alias(self):
        target = "BBCOne.uk"
        exact = self.make_candidate("BBCOne.uk")
        alias = self.make_candidate("BBCOne.uk@London")
        chosen = sorted([alias, exact], key=lambda c: mod.candidate_score(target, c))[0]
        self.assertEqual(chosen.source_xmltv_id, target)

    def test_english_listing_beats_non_english_alias(self):
        target = "Example.us"
        english = self.make_candidate("Example.us@HD", lang="en", site="z.example")
        other = self.make_candidate("Example.us@SD", lang="fr", site="a.example")
        chosen = sorted([other, english], key=lambda c: mod.candidate_score(target, c))[0]
        self.assertEqual(chosen.channel.attrib["lang"], "en")

    def test_clone_rewrites_xmltv_id_for_kodi_mapping(self):
        candidate = self.make_candidate("BBCOne.uk@London")
        cloned = mod.clone_for_target(candidate, "BBCOne.uk")
        self.assertEqual(cloned.attrib["xmltv_id"], "BBCOne.uk")
        self.assertEqual(cloned.attrib["site_id"], "1")


if __name__ == "__main__":
    unittest.main()
