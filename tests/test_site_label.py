import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analyze import weeks as W  # noqa: E402


class SiteLabelTest(unittest.TestCase):
    def test_site_keeps_last_published_week_while_new_week_is_pending(self):
        real = W.week_data
        with mock.patch.object(W, "latest_label", return_value="2099-W01"), \
                mock.patch.object(W, "labels", return_value=W.labels() + ["2099-W01"]), \
                mock.patch.object(W, "week_data", side_effect=lambda l: {"trends": []} if l == "2099-W01" else real(l)):
            self.assertNotEqual("2099-W01", W.site_label())
            self.assertNotIn("2099-W01", [w for w, _ in W.archive_weeks()])


if __name__ == "__main__":
    unittest.main()
