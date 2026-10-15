"""Gated download: AES-GCM round trip (Python) and the real browser flow (wrong password rejected, right password yields valid PDF / PPTX)."""
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from render import enc  # noqa: E402
from tests.test_api import build_once  # noqa: E402


class CryptoTests(unittest.TestCase):
    def test_round_trip_and_wrong_password(self):
        blob = enc.encrypt({"a": "日本語"}, "pw1")
        self.assertEqual({"a": "日本語"}, enc.decrypt(blob, "pw1"))
        with self.assertRaises(Exception):
            enc.decrypt(blob, "pw2")

    def test_each_blob_uses_fresh_salt_and_iv(self):
        a, b = enc.encrypt({"x": 1}, "pw"), enc.encrypt({"x": 1}, "pw")
        self.assertNotEqual((a["salt"], a["iv"]), (b["salt"], b["iv"]))


class BrowserDownloadTests(unittest.TestCase):
    def test_wrong_password_rejected_right_password_downloads_valid_files(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("playwright not installed")
        build_once()
        from pptx import Presentation
        pw = enc.get_password()
        srv = subprocess.Popen([sys.executable, "-m", "http.server", "8771", "--directory", str(ROOT / "site")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
        try:
            with sync_playwright() as p, tempfile.TemporaryDirectory() as d:
                b = p.chromium.launch()
                page = b.new_page(accept_downloads=True)
                page.goto("http://localhost:8771/index.html")
                page.wait_for_selector(".card")
                self.assertEqual(0, page.locator(".card a[download]").count())
                page.locator(".selbox").nth(0).check()
                page.locator(".selbox").nth(1).check()
                for kind, btn in (("pdf", "#dlpdf"), ("pptx", "#dlpptx")):
                    page.click(btn)
                    page.fill("#pwin", "definitely-wrong")
                    page.click("#pwform button[type=submit]")
                    page.wait_for_function("document.getElementById('pwerr').textContent.includes('違います')")
                    page.fill("#pwin", pw)
                    with page.expect_download() as dl:
                        page.click("#pwform button[type=submit]")
                    f = Path(d) / dl.value.suggested_filename
                    dl.value.save_as(str(f))
                    if kind == "pdf":
                        self.assertTrue(f.read_bytes().startswith(b"%PDF"))
                        self.assertEqual(4, f.read_bytes().count(b"/Type /Page "))
                    else:
                        self.assertEqual(4, len(Presentation(str(f)).slides))
                b.close()
        finally:
            srv.terminate()


if __name__ == "__main__":
    unittest.main()
