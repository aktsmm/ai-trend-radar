import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyze import pending as P


def t(primary, *mentions):
    return {"primary": {"url": primary}, "sources": [{"url": u} for u in mentions]}


class VendorLinksTest(unittest.TestCase):
    def test_picks_vendor_page_behind_a_catalog_primary(self):
        x = t("https://openrouter.ai/moonshotai/kimi-k3.1-pro", "https://www.kimi.ai/blog/kimi-k3-1-pro", "https://www.reddit.com/r/x/1", "https://evil.example/kimi")
        self.assertEqual(["https://www.kimi.ai/blog/kimi-k3-1-pro"], P.vendor_links(x))

    def test_only_https_allowlisted_and_not_the_primary(self):
        x = t("https://www.liquid.ai/blog/lfm3", "https://www.liquid.ai/blog/lfm3", "http://www.liquid.ai/blog/old", "https://notliquid.ai/x", "https://liquid.ai.evil.example/x")
        self.assertEqual([], P.vendor_links(x))

    def test_limit(self):
        x = t("https://a.example/", *[f"https://www.liquid.ai/blog/p{i}" for i in range(5)])
        self.assertEqual(2, len(P.vendor_links(x)))


if __name__ == "__main__":
    unittest.main()
