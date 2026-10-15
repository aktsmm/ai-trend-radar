"""Merge per-entity research proposals (status publish) into data/reports/<week>/{enrichment,digest,slides,decks}.json.

python -m analyze.ingest --week 2026-W42 --proposals DIR   # then run: python -m analyze.digest_gate --week 2026-W42
Rejected proposals are recorded in data/reports/<week>/rejected_candidates.json (reason shown on the site's candidate list).
Nothing here trusts the proposal: the gate must pass afterwards.
"""
import argparse
import json
from pathlib import Path

from collect.common import ROOT


def _load(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _dump(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True)
    ap.add_argument("--proposals", required=True)
    a = ap.parse_args()
    wk = ROOT / "data" / "reports" / a.week
    enr, dg, sl, dk = (_load(wk / f, {}) for f in ("enrichment.json", "digest.json", "slides.json", "decks.json"))
    rej = _load(wk / "rejected_candidates.json", {})
    for p in sorted(Path(a.proposals).glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        eid = d["entity_id"]
        if d["status"] == "reject":
            rej[eid] = d["reason"]
            continue
        enr["entities"][eid] = d["enrichment"]
        dg[eid], sl[eid], dk[eid] = d["digest"], d["slides"], d["deck"]
        rej.pop(eid, None)
    for f, o in (("enrichment.json", enr), ("digest.json", dg), ("slides.json", sl), ("decks.json", dk), ("rejected_candidates.json", rej)):
        _dump(wk / f, o)
    print("published:", len(dk), "rejected:", len(rej))


if __name__ == "__main__":
    main()
