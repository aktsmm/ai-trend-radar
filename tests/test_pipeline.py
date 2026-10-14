"""Deterministic pipeline tests on a fixed fixture (no network): python -m unittest discover -s tests"""
import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analyze import build as B  # noqa: E402
from analyze import report as R  # noqa: E402

NOW = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
STATUS = {"sources": {"x_search": {"ok": False, "note": "unavailable"}, "x_watch": {"ok": False}}}
KINDS = {"model", "release", "product", "paper", "hardware", "repo"}


def run(xposts=None, drop=()):
    items = [i for i in json.loads((ROOT / "tests" / "fixtures" / "items.json").read_text(encoding="utf-8")) if i["source"] not in drop]
    for n, i in enumerate(items):
        i["_i"] = n
    return R.build_report(copy.deepcopy(items), STATUS, NOW, None, xposts, {}, None, True, 0, {}, [])


class PipelineTests(unittest.TestCase):
    def test_deterministic(self):
        a, b = run(), run()
        for r in (a, b):
            r.pop("generated_at"); r.pop("last_successful_report_at")
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_no_concepts_or_vendors_in_top(self):
        stop = R.load_stoplist()
        trends = run()["trends"]
        self.assertTrue(trends)
        for t in trends:
            self.assertNotIn(B.norm(t["keyword"]).strip(), stop, t["keyword"])
            self.assertIn(t["kind"], KINDS)

    def test_every_item_has_primary_source_and_date(self):
        for t in run()["trends"]:
            self.assertTrue(t["primary"]["url"].startswith("https://"))
            self.assertTrue(t["primary"]["published_at"] or t["primary"]["date_basis"] == "observed")

    def test_out_of_window_goes_pending(self):
        rep = run()
        self.assertNotIn("Bar3", [t["keyword"] for t in rep["trends"]])
        self.assertIn("Bar3", [p["keyword"] for p in rep["pending"]])

    def test_same_vendor_same_category_is_merged(self):
        trends = run()["trends"]
        names = [t["keyword"] for t in trends]
        self.assertFalse({"Qwen9", "Wan9"} <= set(names), "Alibaba model candidates should be merged into one")
        merged = [t for t in trends if t["related"]]
        self.assertTrue(merged)

    def test_x_failure_does_not_change_top(self):
        with_x = {"1": {"id": "1", "url": "https://x.com/a/status/1", "author": "a", "text": "Foo2 is out", "likes": 500, "reposts": 50,
                        "views": 10000, "_cited": [], "_via": "watchlist"}}
        self.assertEqual([t["keyword"] for t in run(with_x)["trends"]], [t["keyword"] for t in run(None)["trends"]])

    def test_source_outage_keeps_core_ranking(self):
        full = [t["keyword"] for t in run()["trends"]]
        degraded = [t["keyword"] for t in run(drop=("lobsters",))["trends"]]
        self.assertEqual(full[0], degraded[0])
        self.assertTrue({"Foo2", "llama.cpp"} <= set(degraded[:3]))

    def test_official_release_is_primary_for_runtime(self):
        t = next(t for t in run()["trends"] if t["keyword"] == "llama.cpp")
        self.assertEqual(t["primary"]["source_type"], "release_note")
        self.assertEqual(t["category"], "local-runtime")


if __name__ == "__main__":
    unittest.main()
