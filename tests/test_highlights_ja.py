import unittest

from analyze import automerge_check
from analyze import digest_gate as G

SRC = [{"url": "https://openai.com/index/a", "title": "ChatGPT Enterprise now available in AWS Marketplace", "vendor": "OpenAI",
        "date": "2026-11-10", "excerpt": "Customers can buy ChatGPT Enterprise through AWS Marketplace and apply 3 existing AWS commitments to it."},
       {"url": "https://openai.com/index/b", "title": "Short one", "vendor": "OpenAI", "date": "2026-11-10", "excerpt": ""}]
GOOD = {"url": SRC[0]["url"], "title_ja": "ChatGPT Enterprise が AWS Marketplace で購入可能に",
        "summary": "ChatGPT Enterprise を AWS Marketplace から購入でき、既存の AWS の契約枠のうち 3 件を充当できると発表されました。"}


class HighlightsGateTest(unittest.TestCase):
    def test_good_entry_passes(self):
        self.assertEqual(G.check_highlights([GOOD], SRC), [])

    def test_title_only_entry_for_item_without_excerpt(self):
        ok = {"url": SRC[1]["url"], "title_ja": "短い発表の邦題です", "summary": ""}
        self.assertEqual(G.check_highlights([ok], SRC), [])
        bad = {**ok, "summary": "抜粋が無いのに要約を書いている例で、根拠がありません。ゲートが拒否します。"}
        self.assertTrue(any("excerpt" in e for e in G.check_highlights([bad], SRC)))

    def test_rejects_invented_numbers_urls_unknown_items_and_english_titles(self):
        cases = {"number": {**GOOD, "summary": GOOD["summary"] + "価格は 40 % 下がります。"},
                 "URL": {**GOOD, "summary": GOOD["summary"] + " https://example.com"},
                 "not one of": {**GOOD, "url": "https://example.com/x"},
                 "Japanese": {**GOOD, "title_ja": "ChatGPT Enterprise on AWS Marketplace"},
                 "keys": {"url": GOOD["url"], "title_ja": GOOD["title_ja"]}}
        for needle, entry in cases.items():
            self.assertTrue(any(needle in e for e in G.check_highlights([entry], SRC)), needle)

    def test_duplicates_and_non_list(self):
        self.assertTrue(any("duplicate" in e for e in G.check_highlights([GOOD, GOOD], SRC)))
        self.assertTrue(G.check_highlights({}, SRC))

    def test_automerge_allows_the_file(self):
        self.assertTrue(automerge_check.REPORT.match("data/reports/2026-W46/highlights_ja.json"))


if __name__ == "__main__":
    unittest.main()
