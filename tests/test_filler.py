import unittest

from analyze import digest_gate as G


class FillerTest(unittest.TestCase):
    def test_good(self):
        d = {"summary": ["Ollama 0.9 で Qwen3 を手元の GPU から呼び出せるようになりました。", "量子化済みの重みを自動で選びます。"], "why_trending": "ローカルで動かせる大型モデルが増え、導入の手間が減ったため。"}
        self.assertEqual(G.filler_problems("e", d), [])

    def test_filler_dup_short(self):
        self.assertTrue(G.filler_problems("e", {"summary": ["詳細は公式サイトをご覧ください。", "短い"], "why_trending": "今後の動向に注目です"}))
        x = "同じ文をそのまま二回書いている悪い例の文章です。"
        self.assertTrue(G.filler_problems("e", {"summary": [x, x], "why_trending": "理由は十分に長い一文として書いておきます。"}))


if __name__ == "__main__":
    unittest.main()
