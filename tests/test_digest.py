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
        self.dk = load("decks.json")
        self.cur = {"digest": self.dg, "slides": self.sl, "decks": self.dk}

    def prop(self):
        return {"digest": copy.deepcopy(self.dg), "slides": copy.deepcopy(self.sl), "decks": copy.deepcopy(self.dk)}

    def test_committed_data_passes_the_gate(self):
        for eid in self.dg:
            self.assertEqual([], G.check_entity(eid, self.dg[eid], self.sl[eid], self.dk[eid], self.enr, self.window))

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
        p["digest"]["llama-cpp"], p["slides"]["llama-cpp"], p["decks"]["llama-cpp"] = p["digest"]["ollama"], p["slides"]["ollama"], p["decks"]["ollama"]
        ok, problems = G.check_batch(p, self.enr, self.window, self.cur)
        self.assertNotIn("llama-cpp", ok)
        self.assertTrue(any("llama-cpp" in x for x in problems))

    def test_unchanged_proposal_changes_nothing(self):
        self.assertEqual(([], []), G.check_batch(self.prop(), self.enr, self.window, self.cur))

    def test_all_committed_decks_pass_and_every_trend_with_deck_has_digest_and_slide(self):
        dk = load("decks.json")
        self.assertEqual(set(dk), set(self.dg))
        self.assertEqual(set(dk), set(self.sl))
        self.assertEqual(0, G.main(["--week", "2026-W42"]))

    def test_deletion_is_rejected(self):
        p = self.prop()
        for k in ("digest", "slides", "decks"):
            p[k].pop("ollama", None)
        p["decks"] = load("decks.json")
        p["decks"].pop("ollama")
        ok, problems = G.check_batch(p, self.enr, self.window, self.cur)
        self.assertTrue(any("deleted" in x for x in problems))

    def test_slide_only_change_is_counted_and_validated(self):
        p = self.prop()
        p["decks"] = load("decks.json")
        cur = self.cur
        p["slides"]["ollama"][0]["official_url"] = "https://evil.example/"
        ok, problems = G.check_batch(p, self.enr, self.window, self.cur)
        self.assertNotIn("ollama", ok)
        self.assertTrue(problems)

    def test_date_must_match_captured_publication_date(self):
        p = self.prop()
        p["decks"] = load("decks.json")
        p["decks"]["ollama"]["sources"][0]["date"] = "2026-10-09"
        ok, problems = G.check_batch(p, self.enr, self.window, self.cur)
        self.assertTrue(any("captured publication date" in x for x in problems))

    def test_deck_refs_must_resolve(self):
        p = self.prop()
        p["decks"] = load("decks.json")
        p["decks"]["ollama"]["overview"]["refs"] = ["s4"]
        self.assertTrue(G.check_batch(p, self.enr, self.window, None)[1])


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
