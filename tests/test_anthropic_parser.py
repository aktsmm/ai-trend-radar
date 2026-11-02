import unittest

from collect.official import parse_anthropic_news

CARD = ('<article><header><p><a href="/news/announcements">Announcements</a></p><time>Oct 18, 2026</time></header>'
        '<a class="m" href="/news/public-benefit-fund"><img alt="Investing in the public benefit" src="/x.jpg"/></a>'
        '<a class="t" href="/news/public-benefit-fund"><h3>Investing in the <b>public</b> benefit</h3><p>summary</p></a></article>'
        '<article><header><time>Oct 20, 2026</time></header><a href="/news/claude-x"><img alt="Claude X" src="/y.jpg"/></a></article>')
OLD = '<a href="/news/old-post">Oct 1, 2026 Product Old post title</a>'
ROW = ('<a href="/news/expanding-partnership-gsa">Expanding our partnership with GSA</a>'
       '<a href="/news/partnerships">Partnerships</a><time>Oct 27, 2026</time>'
       '<div role="region" aria-label="Expanding our partnership with GSA details"></div>'
       '<a href="/news/s1-sec">S-1 filed</a><a href="/news/announcements">Announcements</a><time>Oct 26, 2026</time>'
       '<div role="region" aria-label="Anthropic files S-1 details"></div>')


class AnthropicNewsParserTest(unittest.TestCase):
    def test_card_layout(self):
        got = parse_anthropic_news(CARD)
        self.assertEqual([g[1] for g in got], ["https://www.anthropic.com/news/public-benefit-fund", "https://www.anthropic.com/news/claude-x"])
        self.assertEqual(got[0][0], "Investing in the public benefit")
        self.assertEqual(got[1][0], "Claude X")

    def test_category_links_are_not_posts(self):
        self.assertTrue(all("announcements" not in g[1] for g in parse_anthropic_news(CARD)))

    def test_row_layout_links_precede_the_date_and_categories_are_skipped(self):
        got = parse_anthropic_news(ROW)
        self.assertEqual([g[1].rsplit("/", 1)[1] for g in got], ["expanding-partnership-gsa", "s1-sec"])
        self.assertEqual(got[1][0], "Anthropic files S-1")

    def test_old_layout_still_parses(self):
        self.assertEqual(len(parse_anthropic_news(OLD)), 1)


if __name__ == "__main__":
    unittest.main()
