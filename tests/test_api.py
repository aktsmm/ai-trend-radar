"""Contract tests for the static JSON API and the assembled site payload (run after `python -m render.build_site`)."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SITE = ROOT / "site"
DATA = json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))
PUB = [t for t in DATA["trends"] if t.get("deck")]


def build_once():
    if not (SITE / "api" / "v1" / "index.json").exists():
        from render import build_site
        sys.argv = [sys.argv[0]]
        build_site.main()


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_once()
        cls.api = SITE / "api" / "v1"

    def j(self, *p):
        return json.loads(self.api.joinpath(*p).read_text(encoding="utf-8"))

    def test_index_and_latest_are_consistent(self):
        idx, latest = self.j("index.json"), self.j("latest.json")
        self.assertEqual(1, idx["version"])
        self.assertEqual(DATA["window"]["label"], idx["latest_week"])
        self.assertEqual(len(PUB), latest["count"])
        self.assertEqual([t["entity_id"] for t in PUB], [i["id"] for i in latest["items"]])

    def test_every_item_has_detail_and_files(self):
        for i in self.j("latest.json")["items"]:
            self.assertTrue((self.api / "keywords" / f"{i['id']}.json").exists(), i["id"])
            for k in ("infographic", "pdf", "pptx"):
                self.assertTrue((SITE / i["urls"][k]).exists(), i["urls"][k])
            self.assertTrue(i["headline"] and i["summary"] and i["official_urls"])

    def test_no_unverified_or_raw_fields_leak(self):
        text = (self.api / "latest.json").read_text(encoding="utf-8") + (self.api / "keywords" / f"{PUB[0]['entity_id']}.json").read_text(encoding="utf-8")
        for bad in ("score_breakdown", "x_posts", "candidates_pool"):
            self.assertNotIn(bad, text)
        for i in self.j("latest.json")["items"]:
            self.assertNotEqual("unverified", i["verification"]["status"])

    def test_candidates_cover_everything_not_published(self):
        ids = {c["id"] for c in self.j("candidates.json")["items"]}
        self.assertEqual({t["entity_id"] for t in DATA["trends"]} - {t["entity_id"] for t in PUB}, ids)


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_once()

    def test_html_links_resolve_to_built_files(self):
        for page in ("index.html", "archive.html"):
            html = (SITE / page).read_text(encoding="utf-8")
            for ref in re.findall(r'(?:href|src)="([^"#$]+?)"', html):
                if ref.startswith(("http", "mailto")) or "${" in ref:
                    continue
                self.assertTrue((SITE / ref).exists(), f"{page}: {ref}")

    def test_weekly_bundle_exists_and_no_stale_entity_files(self):
        label = DATA["window"]["label"]
        for f in (f"weekly-{label}.pdf", f"weekly-{label}.pptx"):
            self.assertTrue((SITE / "downloads" / f).exists(), f)
        ids = {t["entity_id"] for t in PUB}
        have = {p.stem for p in (SITE / "downloads").glob("*.pdf") if not p.stem.startswith("weekly-")}
        self.assertEqual(ids, have)


if __name__ == "__main__":
    unittest.main()
