"""Re-apply committed enrichment (verification, digest, infographic, deck) onto data/trends.json and site/data.js without re-collecting.

python -m analyze.apply
"""
import json

from analyze.report import apply_enrichment
from collect.common import ROOT


def write_if_changed(path, text):
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main():
    p = ROOT / "data" / "trends.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    for t in d["trends"]:  # start from the un-enriched shape so removed entries disappear
        for k in ("digest", "deck"):
            t.pop(k, None)
        t["slides"] = []
    apply_enrichment(d["trends"], d["window"]["label"])
    d["rejected_candidates"] = json.loads((ROOT / "data" / "reports" / d["window"]["label"] / "rejected_candidates.json").read_text(encoding="utf-8")) \
        if (ROOT / "data" / "reports" / d["window"]["label"] / "rejected_candidates.json").exists() else {}
    a = write_if_changed(p, json.dumps(d, ensure_ascii=False, indent=1))
    b = write_if_changed(ROOT / "site" / "data.js", "window.TRENDS = " + json.dumps(d, ensure_ascii=False) + ";\n")
    print("changed:" if a or b else "unchanged:", "data/trends.json" if a else "", "site/data.js" if b else "")
    print("applied:", sum(1 for t in d["trends"] if t.get("deck")), "decks,", sum(1 for t in d["trends"] if t.get("digest")), "digests")


if __name__ == "__main__":
    main()
