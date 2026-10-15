import json
import unittest

from analyze import glossary, weeks as W


class GlossaryTest(unittest.TestCase):
    def test_base_entries_complete(self):
        b = glossary.base()
        self.assertGreaterEqual(len(b), 15)
        for e in b:
            self.assertTrue(e["term"] and e["short"] and e["explain"])
            self.assertIn(e["kind"], ("基礎", "仕組み"))
        self.assertEqual(len({glossary._norm(e["term"]) for e in b}), len(b))

    def test_merge_has_item_terms(self):
        items = glossary.glossary_items(W.archive_weeks())
        self.assertGreater(len(items), len(glossary.base()))
        json.dumps(items, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
