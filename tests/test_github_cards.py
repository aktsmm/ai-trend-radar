import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from analyze import github_top as T

ROOT = Path(__file__).resolve().parent.parent


def items(n, tags=None):
    tags = tags or ["coding-agent"] * n
    return [{"rank": i + 1, "repo": f"o{i}/r{i}", "url": f"https://github.com/o{i}/r{i}", "stars_week": 1000 - i, "stars_total": 5000,
             "language": "Go", "description": f"AI tool {i}", "tag": tags[i]} for i in range(n)]


class PlanTest(unittest.TestCase):
    def check(self, cards, n):
        self.assertEqual(T.card_problems(cards), [])
        self.assertEqual(sum(len(c["members"]) for c in cards), n, "every repo is in exactly one card")

    def test_top_three_single_and_rest_grouped_by_field(self):
        tags = ["coding-agent"] * 3 + ["data", "data", "coding-agent", "coding-agent", "coding-agent", "coding-agent", "coding-agent"]
        cards = T.plan_cards(items(10, tags))
        self.check(cards, 10)
        self.assertEqual([c["mode"] for c in cards[:3]], ["single"] * 3)
        self.assertTrue(all(2 <= len(c["members"]) <= 3 for c in cards[3:]), [len(c["members"]) for c in cards])
        self.assertEqual({c["tag"] for c in cards[3:]}, {"data", "coding-agent"})

    def test_balanced_chunks_and_unique_ids(self):
        cards = T.plan_cards(items(9))
        self.check(cards, 9)
        self.assertEqual([len(c["members"]) for c in cards[3:]], [3, 3])
        self.assertEqual(len({c["entity_id"] for c in cards}), len(cards))
        self.assertEqual([len(g) for g in T._chunks(list(range(5)))], [3, 2])
        self.assertEqual([len(g) for g in T._chunks(list(range(4)))], [2, 2])

    def test_lone_fields_are_not_left_as_one_repo_cards(self):
        tags = ["coding-agent"] * 3 + ["data", "infra", "media", "coding-agent", "coding-agent", "coding-agent", "coding-agent"]
        cards = T.plan_cards(items(10, tags))
        self.check(cards, 10)
        self.assertTrue(all(len(c["members"]) >= 2 for c in cards[3:]), [(c["tag"], len(c["members"])) for c in cards[3:]])

    def test_small_inputs(self):
        for n in (1, 3, 4, 5):
            self.check(T.plan_cards(items(n)), n)


class TrendEntryTest(unittest.TestCase):
    def test_cards_are_valid_trend_entries_and_skip_covered_repos(self):
        week = "2099-W01"
        d = ROOT / "data" / "reports" / week
        d.mkdir(parents=True, exist_ok=True)
        try:
            cards = T.plan_cards(items(6, ["data"] * 6))
            (d / "github_cards.json").write_text(json.dumps(cards), encoding="utf-8")
            out = T.card_trends(week, {"https://github.com/o0/r0"}, first_rank=5)
            self.assertNotIn("https://github.com/o0/r0", [m["url"] for t in out for m in t["members"]])
            self.assertEqual([t["rank"] for t in out], list(range(5, 5 + len(out))))
            schema = json.loads((ROOT / "schema" / "trend.schema.json").read_text(encoding="utf-8"))
            doc = {"generated_at": "2099-01-01T00:00:00Z", "window": {"from": "2099-01-01", "to": "2099-01-08"},
                   "trends": [{**t, "verification": {"status": "unverified", "checks": []}} for t in out]}
            errs = [e.message[:120] for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(doc)]
            self.assertEqual(errs, [])
            self.assertTrue(all(t["category"] == "github-trending" and t["kind"] == "repo" and len(t["official_urls"]) <= 3 for t in out))
        finally:
            for f in d.glob("*"):
                f.unlink()
            d.rmdir()

    def test_no_plan_no_cards(self):
        self.assertEqual(T.card_trends("2099-W02", set(), 1), [])


if __name__ == "__main__":
    unittest.main()
