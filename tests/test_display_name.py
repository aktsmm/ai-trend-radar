import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyze.report import display_name


class DisplayNameTest(unittest.TestCase):
    def test_bare_ids_get_the_vendor(self):
        self.assertEqual("Moonshot kimi-k3", display_name("kimi-k3", "Moonshot"))
        self.assertEqual("Liquid lfm2", display_name("lfm2", "Liquid"))

    def test_unchanged(self):
        for kw, v in (("Claude Code", "Anthropic"), ("LFM3", "Liquid"), ("beam", None), ("vLLM", "vLLM"), ("Ollama", "Ollama"), ("ollama", "Ollama"), ("kimi-k3", "")):
            self.assertEqual(kw, display_name(kw, v), (kw, v))


if __name__ == "__main__":
    unittest.main()
