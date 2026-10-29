import json
import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyze import digest_gate as G
from analyze.report import apply_enrichment


class EnrichmentOverridesTest(unittest.TestCase):
    def test_gate_accepts_and_rejects_display_category_kind(self):
        ent = {"verification_status": "verified", "official_urls": ["https://example.com/a"], "checks": [], "display": "NVIDIA Sentry", "category": "dev-tool", "kind": "product"}
        enr = {"entities": {"e": ent}}
        ok = lambda: [p for p in G.check_entity("e", None, None, None, enr, {"from": "2026-10-01", "to": "2026-10-08"}) if "enrichment." in p or "unknown" in p]
        self.assertEqual([], ok())
        for k, v in (("display", "x"), ("display", "<img src=x>"), ("category", "weird"), ("kind", "weird")):
            bad = {"entities": {"e": {**ent, k: v}}}
            probs = [p for p in G.check_entity("e", None, None, None, bad, {"from": "2026-10-01", "to": "2026-10-08"}) if "enrichment." in p or "unknown" in p or "markup" in p]
            self.assertTrue(probs, (k, v))

    def test_apply_enrichment_honours_overrides(self):
        import analyze.report as R
        trends = [{"entity_id": "mlx", "keyword": "MLX", "vendor": "Apple", "category": "research", "kind": "paper", "sources": [], "x_posts": []}]
        enr = {"entities": {"mlx": {"verification_status": "verified", "checks": [], "official_urls": [], "category": "local-runtime", "kind": "product", "display": "Apple MLX"}}}
        real = Path.read_text
        with unittest.mock.patch.object(Path, "exists", lambda self: self.name == "enrichment.json"), \
                unittest.mock.patch.object(Path, "read_text", lambda self, *a, **k: json.dumps(enr) if self.name == "enrichment.json" else real(self, *a, **k)):
            R.apply_enrichment(trends, "2099-W01")
        t = trends[0]
        self.assertEqual(("local-runtime", "product", "Apple MLX"), (t["category"], t["kind"], t["display"]))


if __name__ == "__main__":
    unittest.main()
