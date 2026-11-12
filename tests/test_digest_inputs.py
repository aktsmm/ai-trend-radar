import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from analyze import digest_gate as G
from analyze import prefetch
from analyze import report as R

ROOT = Path(__file__).resolve().parent.parent


class PinnedHighlightsTest(unittest.TestCase):
    """Regression: the rolling window moved past translated announcements, the report was regenerated without them and the gate refused the
    committed translations ("not one of this week's official highlights"), which stopped Pages for two days."""

    def setUp(self):
        self.week = "2099-W05"
        self.dir = ROOT / "data" / "reports" / self.week
        self.dir.mkdir(parents=True, exist_ok=True)
        self.old = {"vendor": "AWS", "title": "Old post", "url": "https://aws.amazon.com/blogs/old", "date": "2099-01-01", "feed": "aws", "excerpt": "x" * 60}
        self.new = {"vendor": "AWS", "title": "New post", "url": "https://aws.amazon.com/blogs/new", "date": "2099-01-08", "feed": "aws", "excerpt": "y" * 60}
        (self.dir / "report.json").write_text(json.dumps({"official_highlights": [self.old]}), encoding="utf-8")
        (self.dir / "highlights_ja.json").write_text(json.dumps([{"url": self.old["url"], "title_ja": "古い投稿", "summary": ""}]), encoding="utf-8")

    def tearDown(self):
        for f in self.dir.glob("*"):
            f.unlink()
        self.dir.rmdir()

    def test_translated_items_survive_the_window_moving(self):
        pinned = R.pinned_highlights(self.week, [self.new])
        self.assertEqual([h["url"] for h in pinned], [self.old["url"]])
        self.assertEqual(pinned[0]["excerpt"], self.old["excerpt"], "the excerpt the summary was written from is kept")

    def test_no_duplicates_and_untranslated_items_are_not_pinned(self):
        self.assertEqual(R.pinned_highlights(self.week, [self.old]), [])
        (self.dir / "highlights_ja.json").write_text("[]", encoding="utf-8")
        self.assertEqual(R.pinned_highlights(self.week, []), [])

    def test_missing_or_broken_files_do_not_raise(self):
        (self.dir / "report.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(R.pinned_highlights(self.week, []), [])
        self.assertEqual(R.pinned_highlights("2099-W06", []), [])

    def test_gate_accepts_a_pinned_translation(self):
        out = G.check_highlights([{"url": self.old["url"], "title_ja": "古い投稿です", "summary": ""}], [self.new, self.old])
        self.assertEqual(out, [])


class PrefetchShapeTest(unittest.TestCase):
    """Regression: `rec, raw = readme_record(url) or (None, "")` unpacked a dict and crashed the digest's input preparation for every repo URL."""

    def test_readme_record_returns_a_record_not_a_pair(self):
        with mock.patch.object(prefetch, "get", return_value="# Tool\n\nDoes a thing."):
            rec = prefetch.readme_record("https://github.com/o/r")
        self.assertIsInstance(rec, dict)
        self.assertEqual(rec["url"], "https://github.com/o/r")
        self.assertIn("Does a thing", rec["text"])
        self.assertIsNone(prefetch.readme_record("https://example.com/x"))

    def test_main_handles_repo_url_candidates_and_cards(self):
        pend = {"week": "x", "window": {}, "candidates": [
            {"entity_id": "plain-repo", "primary": {"url": "https://github.com/o/plain"}},
            {"entity_id": "gh-card", "primary": {"url": "https://github.com/o/a"}, "members": [{"url": "https://github.com/o/a"}, {"url": "https://github.com/o/b"}]},
            {"entity_id": "site", "primary": {"url": "https://example.com/post"}}], "highlights": []}
        work = ROOT / ".work"
        existed = work.exists()
        work.mkdir(exist_ok=True)
        (work / "pending.json").write_text(json.dumps(pend), encoding="utf-8")
        try:
            with mock.patch.object(prefetch, "get", return_value="<html><body><p>Hello world text.</p></body></html>"):
                self.assertEqual(prefetch.main(), None)
            for eid in ("plain-repo", "gh-card", "site"):
                self.assertTrue((work / "pages" / f"{eid}.json").exists(), eid)
            self.assertEqual(len(json.loads((work / "pages" / "gh-card.json").read_text(encoding="utf-8"))["pages"]), 2)
        finally:
            import shutil
            shutil.rmtree(work / "pages", ignore_errors=True)
            (work / "pending.json").unlink(missing_ok=True)
            if not existed:
                work.rmdir()


if __name__ == "__main__":
    unittest.main()
