import unittest

from analyze import github_top as T
from collect import gh_weekly as G

HTML = """
<article class="Box-row"><p class="btn-label">Sponsor</p><p>Star NVIDIA / auto-ontology</p><h2 class="h3 lh-condensed"><a href="/NVIDIA/auto-ontology" data-view-component="true"> <span class="text-normal">NVIDIA /</span> auto-ontology </a></h2>
<p class="col-9 color-fg-muted my-1">Connect scattered data with an LLM-built ontology</p>
<div><span itemprop="programmingLanguage">Python</span>
<a href="/NVIDIA/auto-ontology/stargazers" class="Link"><svg aria-label="star"></svg> 10,964</a>
<span class="d-inline-block float-sm-right">9,327 stars this week</span></div></article>
<article class="Box-row"><h2><a href="/zed-industries/zed">zed-industries / zed</a></h2><p>Code editor</p>
<a href="/zed-industries/zed/stargazers"> 80,000</a><span>1,000 stars this week</span></article>
<article class="Box-row"><h2><a href="/tiny/llm-toy">tiny / llm-toy</a></h2><p>A small LLM toy</p>
<a href="/tiny/llm-toy/stargazers"> 42</a><span>2,000 stars this week</span></article>
"""


class ParseTest(unittest.TestCase):
    def test_parse_trending(self):
        got = G.parse_trending(HTML)
        self.assertEqual([g["repo"] for g in got], ["NVIDIA/auto-ontology", "zed-industries/zed", "tiny/llm-toy"])
        self.assertEqual((got[0]["stars_week"], got[0]["stars_total"], got[0]["language"]), (9327, 10964, "Python"))
        self.assertEqual(got[0]["description"], "Connect scattered data with an LLM-built ontology")

    def test_filter_reasons(self):
        a, b, c = G.parse_trending(HTML)
        self.assertIsNone(G.exclusion(a, []))
        self.assertEqual(G.exclusion(b, []), "not AI related")
        self.assertIn("total stars", G.exclusion(c, []))
        self.assertEqual(G.exclusion({**b, "description": "uncensored model hub"}, []), "promo / unsafe wording")
        self.assertIsNone(G.exclusion(b, ["llm"]))

    def test_build_ranks_by_weekly_stars_and_merges_pages(self):
        pages = [G.parse_trending(HTML), [{"repo": "NVIDIA/auto-ontology", "description": "x llm", "stars_week": 1, "stars_total": 5000, "language": None}]]
        out = G.build(pages, lambda r: ([], None, None))
        self.assertEqual([i["repo"] for i in out["items"]], ["NVIDIA/auto-ontology"])
        self.assertEqual(out["items"][0]["stars_week"], 9327)
        self.assertEqual(len(out["excluded"]), 2)


class ReportTest(unittest.TestCase):
    RAW = {"pages_ok": 5, "pages_total": 5, "excluded": [{"repo": "a/b", "reason": "x"}],
           "items": [{"repo": f"o/r{i}", "url": f"https://github.com/o/r{i}", "stars_week": 100 - i, "stars_total": 900,
                      "description": "An LLM agent", "language": "Go", "topics": []} for i in range(12)]}

    def test_build_keeps_top_ten_and_valid(self):
        r = T.build(self.RAW, "2026-W46")
        self.assertEqual(len(r["items"]), 10)
        self.assertEqual(T.problems(r), [])

    def test_one_liner_survives_a_rebuild(self):
        first = T.build(self.RAW, "2026-W46")
        first["items"][0]["one_liner"] = "手元の資料を AI が読める形に整える道具"
        again = T.build(self.RAW, "2026-W46", previous=first)
        self.assertEqual(again["items"][0]["one_liner"], first["items"][0]["one_liner"])

    def test_problems_catch_bad_data(self):
        r = T.build(self.RAW, "2026-W46")
        r["items"][1]["url"] = "https://evil.example/o/r1"
        r["items"][2]["stars_week"] = 10_000
        r["items"][3]["one_liner"] = "あ" * 81
        text = "\n".join(T.problems(r))
        for needle in ("url must be", "not sorted", "one_liner over"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
