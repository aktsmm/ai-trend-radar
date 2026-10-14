"""Tests for the digest generation gate (plan A) and display-only denoising (plan B)."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
WEEK = ROOT / "data" / "reports" / "2026-W42"

from analyze import digest_gate as G  # noqa: E402
from analyze import report as R  # noqa: E402


def load(n):
    return json.loads((WEEK / n).read_text(encoding="utf-8"))


class GateTests(unittest.TestCase):
    def setUp(self):
        self.enr, self.dg, self.sl = load("enrichment.json"), load("digest.json"), load("slides.json")
        self.window = {"from": "2026-10-08", "to": "2026-10-15"}
        self.cur = {"digest": self.dg, "slides": self.sl}

    def prop(self):
        return {"digest": copy.deepcopy(self.dg), "slides": copy.deepcopy(self.sl)}

    def test_committed_data_passes_the_gate(self):
        for eid in self.dg:
            self.assertEqual([], G.check_entity(eid, self.dg[eid], self.sl[eid], self.enr, self.window))

    def test_unknown_url_is_rejected(self):
        p = self.prop()
        p["slides"]["ollama"][0]["official_url"] = "https://example.com/x"
        ok, problems = G.check_batch(p, self.enr, self.window, self.cur)
        self.assertEqual([], ok)
        self.assertTrue(any("official_url" in x for x in problems))

    def test_out_of_window_date_is_rejected(self):
        p = self.prop()
        p["slides"]["ollama"][0]["source_date"] = "2026-01-01"
        self.assertTrue(G.check_batch(p, self.enr, self.window, self.cur)[1])

    def test_unverified_entity_is_rejected(self):
        p = self.prop()
        p["digest"]["llama-cpp"], p["slides"]["llama-cpp"] = p["digest"]["ollama"], p["slides"]["ollama"]
        ok, problems = G.check_batch(p, self.enr, self.window, self.cur)
        self.assertNotIn("llama-cpp", ok)
        self.assertTrue(any("llama-cpp" in x for x in problems))

    def test_unchanged_proposal_changes_nothing(self):
        self.assertEqual(([], []), G.check_batch(self.prop(), self.enr, self.window, self.cur))


class DenoiseTests(unittest.TestCase):
    def test_body_only_mentions_and_unrelated_x_posts_are_dropped(self):
        t = {"keyword": "Claude Code", "entity_id": "claude-code", "related": [],
             "sources": [{"name": "github_new", "title": "someone/unrelated-repo"}, {"name": "devto", "title": "My Claude Code week"},
                         {"name": "gh_releases", "title": "claude-code v2.1.300"}],
             "x_posts": [{"text": "A hacker story"}, {"text": "Claude Code now supports hooks"}]}
        R.on_topic_filter(t)
        self.assertEqual(["devto", "gh_releases"], [s["name"] for s in t["sources"]])
        self.assertEqual(1, len(t["x_posts"]))


if __name__ == "__main__":
    unittest.main()
