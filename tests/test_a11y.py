"""Static accessibility guards for the hand-written pages: one h1, a skip link that targets an existing id, a language, and no tiny text."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PAGES = ("index.html", "about.html", "archive.html", "glossary.html", "github.html")


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

    def test_badge_and_chip_contrast_meets_aa(self):
        def lum(h):
            h = h.lstrip("#")
            h = "".join(c * 2 for c in h) if len(h) == 3 else h
            c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]
            return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]

        css = (SITE / "style.css").read_text(encoding="utf-8")
        pairs = re.findall(r"(\.(?:tag|badge(?:\.\w+)?)|\.chips button\[aria-pressed=true\])\s*\{([^}]*)\}", css)
        self.assertGreaterEqual(len(pairs), 5)
        for sel, body in pairs:
            bg = re.search(r"background:\s*(#[0-9a-fA-F]{3,6})", body)
            fg = re.search(r"(?<![-\w])color:\s*(#[0-9a-fA-F]{3,6})", body)
            if not (bg and fg):
                continue
            hi, lo = sorted((lum(bg.group(1)), lum(fg.group(1))), reverse=True)
            self.assertGreaterEqual((hi + .05) / (lo + .05), 4.5, f"{sel} {fg.group(1)} on {bg.group(1)}")

class SummaryLayoutTest(unittest.TestCase):
    def test_entity_chips_are_capped_and_truncated(self):
        # long display names (e.g. GitHub bundle cards) and 5 chips per theme overflowed the fixed-height weekly summary image
        js = (SITE / "summary.js").read_text(encoding="utf-8")
        css = (SITE / "summary.css").read_text(encoding="utf-8")
        self.assertIn("x.entities.slice(0, 3)", js)
        self.assertRegex(css, r"\.sm-th \.ch span \{[^}]*text-overflow:\s*ellipsis")


if __name__ == "__main__":
    unittest.main()
