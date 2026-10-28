import gzip
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collect import common


class FakeResp:
    def __init__(self, body):
        self._b = body

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class GzipTest(unittest.TestCase):
    def test_gzipped_body_is_decoded_even_without_a_content_encoding_negotiation(self):
        xml = "<?xml version='1.0'?><rss><channel><item><title>日本語</title></item></channel></rss>"
        with mock.patch("urllib.request.urlopen", return_value=FakeResp(gzip.compress(xml.encode("utf-8")))):
            self.assertEqual(xml, common.get("https://example.com/feed"))

    def test_plain_body_is_unchanged(self):
        with mock.patch("urllib.request.urlopen", return_value=FakeResp("plain text".encode("utf-8"))):
            self.assertEqual("plain text", common.get("https://example.com/x"))


if __name__ == "__main__":
    unittest.main()
