"""Auto-merge allowlist: only report JSON files may be taken from a bot PR; generated files are never trusted."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyze.automerge_check import classify  # noqa: E402


class AllowlistTests(unittest.TestCase):
    def test_report_files_and_generated_are_accepted(self):
        take, gen, bad = classify(["data/reports/2026-W43/digest.json", "data/reports/2026-W43/decks.json", "data/reports/2026-W43/themes.json", "data/trends.json", "site/data.js"])
        self.assertEqual([], bad)
        self.assertEqual(3, len(take))
        self.assertEqual(2, len(gen))

    def test_anything_else_is_rejected(self):
        for p in (".github/workflows/ci.yml", "analyze/digest_gate.py", "schema/trend.schema.json", "tests/test_x.py", "data/reports/2026-W43/report.json",
                  "data/reports/../../x.json", "site/index.html", "requirements.txt"):
            self.assertEqual([p], classify([p])[2], p)

    def test_report_json_alone_counts_as_nothing_to_take(self):
        self.assertEqual([], classify(["data/trends.json"])[0])


if __name__ == "__main__":
    unittest.main()
