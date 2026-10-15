import unittest

from analyze import digest_gate as G

ENR = {"entities": {"e1": {"official_urls": ["https://example.com/a"], "checks": []}}}
DECKS = {"e1": {}}
OK = {"term": "量子化", "kind": "基礎", "short": "数値を粗くして軽くする", "explain": "モデルの重みを細かい数値から粗い数値に置き換え、サイズを小さくする方法です。", "entity": "e1", "ref": "https://example.com/a"}


class GlossaryGateTest(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(G.check_glossary([OK], ENR, DECKS), [])

    def test_duplicate_and_bad_ref(self):
        self.assertTrue(G.check_glossary([OK], ENR, DECKS, {"量子化"}))
        self.assertTrue(G.check_glossary([{**OK, "ref": "https://evil.example/x"}], ENR, DECKS))
        self.assertTrue(G.check_glossary([{**OK, "entity": "zz"}], ENR, DECKS))

    def test_limits(self):
        self.assertTrue(G.check_glossary([{**OK, "explain": "短い"}], ENR, DECKS))
        self.assertTrue(G.check_glossary([{**OK, "term": f"t{i}"} for i in range(7)], ENR, DECKS))
        self.assertTrue(G.check_glossary([{**OK, "extra": 1}], ENR, DECKS))


if __name__ == "__main__":
    unittest.main()
