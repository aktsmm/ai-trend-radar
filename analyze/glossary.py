"""Glossary for beginners: data/glossary.json (curated basics) + the 用語メモ of every published brief (deck.impact.terms), merged by term.

glossary_items(weeks) -> [{term, short, explain, kind, appears_in: [{week, id, keyword}]}]  (basics first, then item-specific terms)
"""
import json
import re

from collect.common import ROOT


def _norm(s):
    return re.sub(r"[\s・/()（）]", "", s).lower()


def base():
    return json.loads((ROOT / "data" / "glossary.json").read_text(encoding="utf-8"))


def glossary_items(weeks):
    """weeks: [(label, data)]. Item terms are linked to the keywords that use them; a term that also exists in the basics keeps the basic explanation."""
    items = {_norm(b["term"]): {"term": b["term"], "short": b["short"], "explain": b["explain"], "kind": b["kind"], "appears_in": []} for b in base()}
    alias = {_norm(b["term"].split("(")[0]): _norm(b["term"]) for b in base()}
    for label, data in weeks:
        for t in data["trends"]:
            for x in ((t.get("deck") or {}).get("impact") or {}).get("terms", []):
                k = _norm(x["t"])
                k = k if k in items else alias.get(k, k)
                it = items.setdefault(k, {"term": x["t"], "short": x["d"], "explain": x["d"], "kind": "項目", "appears_in": []})
                it["appears_in"].append({"week": label, "id": t["entity_id"], "keyword": t["keyword"]})
    out = list(items.values())
    out.sort(key=lambda i: ({"基礎": 0, "仕組み": 1, "項目": 2}.get(i["kind"], 3), i["term"]))
    return out
