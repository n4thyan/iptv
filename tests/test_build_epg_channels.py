import importlib.util
import sys
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_epg_channels.py"
spec = importlib.util.spec_from_file_location("build_epg_channels", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class EpgMapperTests(unittest.TestCase):
    def make_candidate(
        self,
        xmltv_id: str,
        lang: str = "en",
        site: str = "example.com",
        mode: str = "alias",
        name: str = "Example",
    ):
        channel = ET.Element(
            "channel",
            {
                "site": site,
                "lang": lang,
                "xmltv_id": xmltv_id,
                "site_id": "1",
            },
        )
        channel.text = name
        return mod.Candidate(
            channel=channel,
            path=Path(f"sites/{site}/channels.xml"),
            source_xmltv_id=xmltv_id,
            discovery_mode=mode,
        )

    def test_base_id(self):
        self.assertEqual(mod.base_id("BBCOne.uk@London"), "BBCOne.uk")
        self.assertEqual(mod.base_id("BBCOne.uk"), "BBCOne.uk")

    def test_exact_match_beats_alias(self):
        target = "BBCOne.uk"
        exact = self.make_candidate("BBCOne.uk", mode="exact")
        alias = self.make_candidate("BBCOne.uk@London", mode="alias")
        chosen = sorted([alias, exact], key=lambda c: mod.candidate_score(target, c))[0]
        self.assertEqual(chosen.source_xmltv_id, target)

    def test_alias_beats_unmapped_name_fallback(self):
        target = "Example.us"
        alias = self.make_candidate("Example.us@HD", mode="alias")
        name = self.make_candidate("", mode="name")
        chosen = sorted([name, alias], key=lambda c: mod.candidate_score(target, c))[0]
        self.assertEqual(chosen.discovery_mode, "alias")

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

    def test_name_normalization_handles_punctuation_and_accents(self):
        self.assertEqual(mod.normalize_name("Series con Ñ"), "seriesconn")
        self.assertEqual(mod.normalize_name("BBC One HD"), "bbconehd")

    def test_catalog_name_index_only_exposes_unique_base_matches(self):
        wanted = {"Unique.uk", "Other.us"}
        catalog = {
            "Unique.uk": {
                "base_id": "Unique.uk",
                "name": "Unique Channel",
                "playlist_name": "Unique Channel (720p)",
                "alt_names": ["Unique TV"],
            },
            "Other.us": {
                "base_id": "Other.us",
                "name": "Other Network",
                "playlist_name": "Other Network",
                "alt_names": [],
            },
        }
        index, _ = mod.build_name_index(wanted, catalog)
        self.assertEqual(index[mod.normalize_name("Unique TV")], {"Unique.uk"})
        self.assertEqual(index[mod.normalize_name("Other Network")], {"Other.us"})


if __name__ == "__main__":
    unittest.main()
