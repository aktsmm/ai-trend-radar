import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyze import prefetch as P


class HfCardTest(unittest.TestCase):
    def test_card_url_only_for_model_pages(self):
        self.assertEqual("https://huggingface.co/a/b/raw/main/README.md", P.hf_card_url("https://huggingface.co/a/b"))
        self.assertEqual("https://huggingface.co/a/b/raw/main/README.md", P.hf_card_url("https://huggingface.co/a/b/"))
        for u in ("https://huggingface.co/spaces/a", "https://huggingface.co/datasets/a/b/x", "https://github.com/a/b", "https://example.com/a/b"):
            self.assertIsNone(P.hf_card_url(u), u)


if __name__ == "__main__":
    unittest.main()
