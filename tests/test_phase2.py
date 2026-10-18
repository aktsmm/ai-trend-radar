"""Phase-2 tests: committed enrichment/slides data, schema, verification display, deterministic PNG build."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
WEEK = ROOT / "data" / "reports" / "2026-W42"
SCHEMA = json.loads((ROOT / "schema" / "trend.schema.json").read_text(encoding="utf-8"))


def load(name):
    return json.loads((WEEK / name).read_text(encoding="utf-8"))


class EnrichmentTests(unittest.TestCase):
    def setUp(self):
        self.enr, self.slides = load("enrichment.json"), load("slides.json")

    def test_slides_validate_against_schema(self):
        v = Draft202012Validator({"$ref": "#/$defs/slide", "$defs": SCHEMA["$defs"]}, format_checker=FormatChecker())
        for eid, ss in self.slides.items():
            self.assertEqual(1, len(ss), eid)
            for s in ss:
                self.assertEqual("infographic", s["diagram_type"], eid)
                self.assertEqual([], [e.message for e in v.iter_errors(s)], f"{eid}: {s['title']}")

    def test_digest_validates_and_matches_enriched_entities(self):
        v = Draft202012Validator({"$ref": "#/$defs/digest", "$defs": SCHEMA["$defs"]}, format_checker=FormatChecker())
        digest = load("digest.json")
        self.assertEqual(set(digest), set(self.enr["entities"]))
        for eid, g in digest.items():
            self.assertEqual([], [e.message for e in v.iter_errors(g)], eid)

    def test_slide_urls_are_official_urls_of_the_entity(self):
        for eid, ss in self.slides.items():
            allowed = set(self.enr["entities"][eid]["official_urls"])
            for s in ss:
                self.assertIn(s["official_url"], allowed, eid)

    def test_verified_entities_have_records_and_existing_urls(self):
        for eid, e in self.enr["entities"].items():
            self.assertIn(e["verification_status"], {"verified", "partially_verified", "unverified"})
            if e["verification_status"] != "unverified":
                self.assertTrue(e["checks"], eid)
                for c in e["checks"]:
                    self.assertTrue(c["retrieved_at"] and c["evidence_urls"] and c["mcp_name"] and c["query"], eid)
            for u in e["official_urls"]:
                # 403 / 429 = the page answered but blocks datacenter IPs (bot protection, e.g. openai.com from CI); the badge only shows for 200
                self.assertIn(self.enr["url_checks"][u]["status"], (200, 403, 429), u)

    def test_unverified_is_visible_in_site(self):
        js = (ROOT / "site" / "slides.js").read_text(encoding="utf-8")
        self.assertIn("未検証", js)
        html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        self.assertIn("未確認", html)
        self.assertIn("観測候補", html)
        self.assertNotIn("(mock)", html)

    def test_trends_without_enrichment_are_unverified_with_no_slides(self):
        from analyze import report as R
        trends = [{"entity_id": "does-not-exist", "slides": [], "official_urls": [], "official_verified": False}]
        R.apply_enrichment(trends, "2026-W42")
        self.assertEqual(trends[0]["verification"]["status"], "unverified")
        self.assertEqual(trends[0]["slides"], [])

    def test_published_trends_file_validates(self):
        data = json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))
        errs = list(Draft202012Validator(SCHEMA, format_checker=FormatChecker()).iter_errors(data))
        self.assertEqual([], [e.message[:120] for e in errs])


class PngTests(unittest.TestCase):
    def test_png_build_is_deterministic(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("playwright not installed")
        import json
        from analyze import weeks as W
        trends = W.site_data()["trends"]
        eid = next((t["entity_id"] for t in trends if t.get("slides")), None)
        if not eid:
            self.skipTest("no published infographic this week")
        digests = []
        with sync_playwright() as p:
            b = p.chromium.launch()
            for _ in range(2):
                page = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
                page.goto((ROOT / "site" / "slide.html").as_uri() + f"?e={eid}&n=0")
                page.wait_for_selector("body[data-ready='1']")
                digests.append(hashlib.sha256(page.locator(".slide").screenshot()).hexdigest())
                page.close()
            b.close()
        self.assertEqual(digests[0], digests[1])


if __name__ == "__main__":
    unittest.main()
