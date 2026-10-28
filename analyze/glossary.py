"""Glossary for beginners, merged by term from three sources (earlier source wins on a duplicate):
  1. data/glossary.json                    curated basics
  2. data/reports/<week>/glossary.json     terms the weekly digest agent adds (gate: analyze.digest_gate.check_glossary; cites an entity + captured URL)
  3. every published brief's 用語メモ        deck.impact.terms

glossary_items(weeks) -> [{term, short, explain, kind, appears_in: [{week, id, keyword}], source_url?}]
"""
import json
import re

from collect.common import ROOT


def _norm(s):
    return re.sub(r"[\s・/()（）]", "", s).lower()


def base():
    return json.loads((ROOT / "data" / "glossary.json").read_text(encoding="utf-8"))


def weekly(exclude_week=None):
    out = []
    for p in sorted((ROOT / "data" / "reports").glob("*/glossary.json")):
        if p.parent.name != exclude_week:
            out += json.loads(p.read_text(encoding="utf-8"))
    return out


def known_terms(exclude_week=None):
    return {_norm(e["term"]) for e in base() + weekly(exclude_week)}


def glossary_items(weeks):
    """weeks: [(label, data)]."""
    items = {}
    for e in base() + weekly():
        items.setdefault(_norm(e["term"]), {"term": e["term"], "short": e["short"], "explain": e["explain"], "kind": e["kind"], "appears_in": [],
                                            **({"source_url": e["ref"]} if e.get("ref") else {})})
    titles = {t["entity_id"]: (w, t.get("display", t["keyword"])) for w, d in weeks for t in d["trends"]}
    for e in weekly():
        if e["entity"] in titles:
            items[_norm(e["term"])]["appears_in"].append({"week": titles[e["entity"]][0], "id": e["entity"], "keyword": titles[e["entity"]][1]})
    alias = {_norm(k["term"].split("(")[0]): n for n, k in items.items()}
    for label, data in weeks:
        for t in data["trends"]:
            for x in ((t.get("deck") or {}).get("impact") or {}).get("terms", []):
                k = _norm(x["t"])
                k = k if k in items else alias.get(k, k)
                it = items.setdefault(k, {"term": x["t"], "short": x["d"], "explain": x["d"], "kind": "項目", "appears_in": []})
                it["appears_in"].append({"week": label, "id": t["entity_id"], "keyword": t.get("display", t["keyword"])})
    out = list(items.values())
    out.sort(key=lambda i: ({"基礎": 0, "仕組み": 1, "項目": 2}.get(i["kind"], 3), i["term"]))
    return out
