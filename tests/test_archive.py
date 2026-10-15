"""Archive: older weeks are rebuilt from their own report + enrichment and get their own page / API file."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analyze import weeks as W  # noqa: E402
from render import build_site  # noqa: E402


class ArchiveTests(unittest.TestCase):
    def test_older_week_is_rederived_from_its_own_files(self):
        latest = W.latest_label()
        with tempfile.TemporaryDirectory() as d:
            rep = Path(d) / "2026-W41"
            shutil.copytree(ROOT / "data" / "reports" / latest, rep)
            r = json.loads((rep / "report.json").read_text(encoding="utf-8"))
            r["window"]["label"] = "2026-W41"
            (rep / "report.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
            old_reports = W.REPORTS
            W.REPORTS = Path(d)
            try:
                self.assertIn("2026-W41", W.labels())
                data = W.week_data("2026-W41")
            finally:
                W.REPORTS = old_reports
        self.assertEqual("2026-W41", data["window"]["label"])
        self.assertIn("themes", data)
        self.assertIn("rejected_candidates", data)

    def test_week_page_repoints_shared_assets_but_keeps_local_data(self):
        html = build_site.week_index_html("2026-W41")
        self.assertIn('href="../../style.css"', html)
        self.assertIn('src="../../app.js"', html)
        self.assertIn('src="data.js"', html)
        self.assertIn("最新の週へ", html)

    def test_latest_week_is_in_the_archive_list(self):
        self.assertIn(W.latest_label(), [w for w, _ in W.archive_weeks()])


if __name__ == "__main__":
    unittest.main()
