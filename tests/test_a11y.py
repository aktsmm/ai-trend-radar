"""Static accessibility guards for the hand-written pages: one h1, a skip link that targets an existing id, a language, and no tiny text."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PAGES = ("index.html", "about.html", "archive.html", "glossary.html")


class A11yTest(unittest.TestCase):
    def test_pages(self):
        for p in PAGES:
            h = (SITE / p).read_text(encoding="utf-8")
            self.assertEqual(1, len(re.findall(r"<h1[\s>]", h)), f"{p}: exactly one h1")
            self.assertIn('<html lang="ja">', h, p)
            m = re.search(r'<a class="skip" href="#([^"]+)"', h)
            self.assertTrue(m, f"{p}: skip link")
            self.assertEqual(1, len(re.findall(r'id="%s"' % re.escape(m.group(1)), h)), f"{p}: skip target #{m.group(1)}")

    def test_no_text_below_12px(self):
        css = (SITE / "style.css").read_text(encoding="utf-8")
        small = re.findall(r"font-size:\s*(?:[0-9]|1[01])(?:\.\d+)?px", css)
        self.assertEqual([], small)

    def test_touch_targets_rule_exists(self):
        css = (SITE / "style.css").read_text(encoding="utf-8")
        m = re.search(r"@media \(pointer:coarse\)\{(.*)\}\s*$", css, re.S) or re.search(r"@media \(pointer:coarse\)\{(.*?)\}\}", css, re.S)
        self.assertTrue(m, "coarse-pointer block")
        for sel in ("button", "summary", "select", "table.cand a", ".chips a", "min-height:44px"):
            self.assertIn(sel, m.group(1), sel)

if __name__ == "__main__":
    unittest.main()
