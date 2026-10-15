"""Browser download flow: filter -> everything visible is checked -> uncheck some -> PDF / PPTX of the checked items only."""
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tests.test_api import build_once  # noqa: E402


class BrowserDownloadTests(unittest.TestCase):
    def test_filtered_checked_items_download_as_valid_pdf_and_pptx(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("playwright not installed")
        build_once()
        from pptx import Presentation
        srv = subprocess.Popen([sys.executable, "-m", "http.server", "8771", "--directory", str(ROOT / "site")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
        try:
            with sync_playwright() as p, tempfile.TemporaryDirectory() as d:
                b = p.chromium.launch()
                page = b.new_page(accept_downloads=True)
                page.goto("http://localhost:8771/index.html")
                page.wait_for_selector(".card")
                total = page.locator(".card").count()
                self.assertEqual(total, page.locator(".selbox:checked").count())  # everything is checked by default
                page.select_option("#kindSel", "model")
                n_model = page.locator(".card").count()
                self.assertTrue(0 < n_model < total)
                self.assertEqual(n_model, page.locator(".selbox:checked").count())  # a new filter starts all-checked
                page.locator(".selbox").first.uncheck()
                self.assertIn(f"{n_model - 1} / {n_model}", page.locator("#selcount").inner_text())
                for kind, btn in (("pdf", "#dlpdf"), ("pptx", "#dlpptx")):
                    with page.expect_download() as dl:
                        page.click(btn)
                    f = Path(d) / dl.value.suggested_filename
                    dl.value.save_as(str(f))
                    pages = (n_model - 1) * 2
                    if kind == "pdf":
                        self.assertTrue(f.read_bytes().startswith(b"%PDF"))
                        self.assertEqual(pages, f.read_bytes().count(b"/Type /Page "))
                    else:
                        self.assertEqual(pages, len(Presentation(str(f)).slides))
                self.assertEqual(0, page.locator(".card a[download]").count())
                b.close()
        finally:
            srv.terminate()


if __name__ == "__main__":
    unittest.main()
