import unittest
from unittest import mock

from analyze import source_health as S
from collect import official as O


def ledger(**kw):
    return {"ok": True, "count": 0, "url": "https://www.liquid.ai/news", **kw}


class RedirectAndQuietTest(unittest.TestCase):
    def test_redirect_to_a_narrower_page_is_reported(self):
        led = ledger(url="https://www.liquid.ai/blog", links=31, newest="2026-10-27", final_url="https://www.liquid.ai/news/models")
        self.assertIn("転送", S._redirect_finding("liquid-blog", led))

    def test_trailing_slash_www_and_fragment_are_not_redirects(self):
        for url, final in (("https://www.kimi.com/blog", "https://www.kimi.com/blog/"), ("https://www.x.com/news", "https://x.com/news"),
                           ("https://a.com/b", "https://a.com/b?ref=1")):
            self.assertIsNone(S._redirect_finding("x", ledger(url=url, links=3, final_url=final)), url)

    def test_old_ledgers_without_the_new_fields_are_not_judged_by_redirect(self):
        self.assertIsNone(S._redirect_finding("x", {"ok": True, "count": 0, "url": "https://a.com/x"}))

    def test_quiet_source_with_links_is_not_flagged_but_markup_change_is(self):
        quiet = ledger(links=23, newest="2026-10-24", final_url="https://www.liquid.ai/news")
        self.assertIsNone(S.judge("ollama-blog", quiet, [{"ollama-blog": quiet}] * 3), "links present, just no recent post")
        broken = ledger(links=0, final_url="https://www.liquid.ai/news")
        self.assertIn("記事リンク", S.judge("x", broken, [{"x": broken}] * 3))

    def test_quiet_rss_feed_with_entries_is_not_flagged_but_an_empty_parse_is(self):
        quiet = {"ok": True, "count": 0, "url": "https://ollama.com/blog/rss.xml", "links": 63, "newest": "2026-10-24"}
        self.assertIsNone(S.judge("ollama-blog", quiet, [{"ollama-blog": quiet}] * 3))
        broken = {**quiet, "links": 0, "newest": None}
        self.assertIn("記事リンク", S.judge("ollama-blog", broken, [{"ollama-blog": broken}] * 3))

    def test_sources_without_the_new_fields_keep_the_old_three_weeks_rule(self):
        old = {"ok": True, "count": 0, "url": "https://a.com/x"}
        self.assertIn("3 週ずっと 0 件", S.judge("x", old, [{"x": old}] * 3))
        self.assertIsNone(S.judge("ml-explore/mlx", old, [{"ml-explore/mlx": old}] * 3))


class SitemapFallbackTest(unittest.TestCase):
    """Regression for the Liquid miss: the index (redirected to a model-only listing) did not list a new post, the sitemap did."""

    INDEX = '<a href="/blog/model-post">m</a>'
    SITEMAP = ("<urlset><url><loc>https://s.test/blog/model-post</loc><lastmod>%(new)s</lastmod></url>"
               "<url><loc>https://s.test/blog/codec</loc><lastmod>%(new)s</lastmod></url>"
               "<url><loc>https://s.test/blog/ancient</loc><lastmod>2020-01-01</lastmod></url>"
               "<url><loc>https://s.test/about</loc><lastmod>%(new)s</lastmod></url>"
               "<url><loc>https://s.test/blog/no-date</loc></url></urlset>")
    ART = '<html><head><title>%s | S</title><meta property="article:published_time" content="%s"></head></html>'
    RX = r'href="(/blog/[a-z0-9][^"#?/]*)"'

    def setUp(self):
        from datetime import datetime, timedelta, timezone
        self.new = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        self.pages = {"https://s.test/blog": self.INDEX, "https://s.test/sitemap.xml": self.SITEMAP % {"new": self.new},
                      "https://s.test/blog/model-post": self.ART % ("Model", self.new), "https://s.test/blog/codec": self.ART % ("Codec", self.new)}

    def run_blog(self):
        with mock.patch.object(O, "get", side_effect=lambda u, **k: self.pages[u]), mock.patch.object(O, "final_url", return_value="https://s.test/blog"):
            return O.fetch_blog(("s-blog", "S", "https://s.test/blog", self.RX))

    def test_post_missing_from_the_index_is_collected_from_the_sitemap(self):
        items = self.run_blog()
        self.assertEqual(sorted(i["url"] for i in items), ["https://s.test/blog/codec", "https://s.test/blog/model-post"])
        self.assertEqual(O.fetch_blog.last["s-blog"]["sitemap_only"], 1)

    def test_only_recent_article_paths_are_taken(self):
        with mock.patch.object(O, "get", side_effect=lambda u, **k: self.pages[u]):
            extra = O.sitemap_recent("https://s.test/blog", self.RX, ["https://s.test/blog/model-post"])
        self.assertEqual(extra, ["https://s.test/blog/codec"])  # not the 2020 post, not /about, not the undated one

    def test_no_sitemap_means_no_change(self):
        def fake(u, **k):
            if u.endswith("sitemap.xml"):
                raise OSError("404")
            return self.pages[u]
        with mock.patch.object(O, "get", side_effect=fake), mock.patch.object(O, "final_url", return_value="https://s.test/blog"):
            items = O.fetch_blog(("s-blog", "S", "https://s.test/blog", self.RX))
        self.assertEqual([i["url"] for i in items], ["https://s.test/blog/model-post"])
        self.assertEqual(O.fetch_blog.last["s-blog"]["sitemap_only"], 0)

    def test_health_flags_an_incomplete_index_even_though_the_post_was_recovered(self):
        led = {"ok": True, "count": 1, "url": "https://s.test/blog", "links": 5, "newest": "2026-11-12", "final_url": "https://s.test/blog", "sitemap_only": 2}
        self.assertIn("サイトマップ", S.judge("s-blog", led, [{"s-blog": led}] * 3))
        self.assertIsNone(S.judge("s-blog", {**led, "sitemap_only": 0}, [{"s-blog": led}] * 3))


class BlogLedgerTest(unittest.TestCase):
    INDEX = '<a href="/blog/new-post">x</a><a href="/blog/old-post">y</a><a href="/blog/new-post">dup</a>'
    ART = '<html><head><title>Hello | Site</title><meta property="article:published_time" content="%s"></head></html>'

    def test_fetch_blog_records_links_newest_and_final_url(self):
        from datetime import datetime, timedelta, timezone
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        old = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%dT00:00:00Z")
        pages = {"https://s.test/news": self.INDEX, "https://s.test/blog/new-post": self.ART % recent, "https://s.test/blog/old-post": self.ART % old}
        with mock.patch.object(O, "get", side_effect=lambda u, **k: pages[u]), mock.patch.object(O, "final_url", return_value="https://s.test/news"):
            items = O.fetch_blog(("t-blog", "T", "https://s.test/news", r'href="(/blog/[a-z0-9][^"#?/]*)"'))
        self.assertEqual([i["url"] for i in items], ["https://s.test/blog/new-post"])
        led = O.fetch_blog.last["t-blog"]
        self.assertEqual((led["links"], led["final_url"]), (2, "https://s.test/news"))
        self.assertEqual(led["newest"], recent[:10])

    def test_liquid_index_is_the_all_posts_page(self):
        liquid = next(b for b in O.BLOG_INDEXES if b[0] == "liquid-blog")
        self.assertEqual(liquid[2], "https://www.liquid.ai/news")  # /blog redirects to /news/models (model posts only)


if __name__ == "__main__":
    unittest.main()
