import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collect import official as O


class BlogDateTest(unittest.TestCase):
    def test_date_formats(self):
        for s in ("October 27, 2026", "Oct 27, 2026", "2026-10-27", "2026-10-27T09:00:00.000Z", "Tue, 27 Oct 2026 10:00:00 GMT"):
            d = O._dt(s)
            self.assertEqual((2026, 10, 27), (d.year, d.month, d.day), s)
        self.assertIsNone(O._dt("not a date"))

    def test_page_dates_in_order_of_trust(self):
        html = '<time datetime="2026-10-27">x</time> "dateModified":"2026-10-30"'
        found = [m.group(1) for r in O.PAGE_DATE_RES for m in [r.search(html)] if m]
        self.assertEqual("2026-10-27", found[0])  # a real publication date beats dateModified
        self.assertIn("2026-10-30", found)

    def test_blog_indexes_are_well_formed(self):
        ids = [b[0] for b in O.BLOG_INDEXES]
        self.assertEqual(len(ids), len(set(ids)))
        for bid, vendor, url, rx in O.BLOG_INDEXES:
            self.assertTrue(url.startswith("https://") and vendor)
            self.assertEqual(1, __import__("re").compile(rx).groups, bid)


if __name__ == "__main__":
    unittest.main()
