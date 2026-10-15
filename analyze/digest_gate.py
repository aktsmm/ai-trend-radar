"""Deterministic gate for LLM-generated digest / infographic / deck JSON (plan A). No LLM call here.

A proposal is a bundle {"digest": {eid: ...}, "slides": {eid: [..]}, "decks": {eid: ..}}. It is accepted per entity only if:
  * the entity has a verified/partially_verified enrichment record,
  * JSON Schema passes (digest / slide / deck),
  * every URL is one of the entity's official URLs or a captured evidence URL,
  * every date is inside the report window and matches the publication date captured for that URL (+-1 day for JST/UTC),
  * deck refs resolve to deck sources, and
  * the number of changed entities stays under a cap; deletions are rejected.

CLI (non-zero exit on any problem; suitable as a required PR check):
  python -m analyze.digest_gate --week 2026-W42 [--proposal DIR] [--base DIR]
Without --proposal the committed data/reports/<week> files are checked. --base enables the change-cap / deletion diff.
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "trend.schema.json").read_text(encoding="utf-8"))
MAX_CHANGED_ENTITIES = 6
FILES = {"digest": "digest.json", "slides": "slides.json", "decks": "decks.json"}


def _validator(name):
    return Draft202012Validator({"$ref": f"#/$defs/{name}", "$defs": SCHEMA["$defs"]}, format_checker=FormatChecker())


def load_bundle(d, missing_ok=False):
    out = {}
    for k, f in FILES.items():
        p = Path(d) / f
        out[k] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else ({} if missing_ok else None)
    return out


def evidence_index(ent):
    """url -> set of captured publication dates (YYYY-MM-DD); official URLs without a captured date map to an empty set."""
    idx = {u: set() for u in ent["official_urls"]}
    for c in ent["checks"]:
        for u in c["evidence_urls"]:
            idx.setdefault(u, set())
            if c.get("evidence_published_at"):
                idx[u].add(c["evidence_published_at"][:10])
    return idx


def _date_ok(d, url, idx, window, who):
    errs = []
    if not (window["from"] <= d <= window["to"]):
        errs.append(f"{who}: date {d} is outside the report window {window['from']}..{window['to']}")
    known = idx.get(url)
    if not known:
        errs.append(f"{who}: date {d} has no captured publication date for {url} (omit the date)")
    else:
        y, m, dd = map(int, d.split("-"))
        near = {(date(y, m, dd) + timedelta(days=k)).isoformat() for k in (-1, 0, 1)}
        if not (near & known):
            errs.append(f"{who}: date {d} does not match the captured publication date {sorted(known)} of {url}")
    return errs


def check_entity(eid, digest, slides, deck, enrichment, window):
    """Return a list of problems (empty list = acceptable)."""
    ent = enrichment["entities"].get(eid)
    if not ent or ent["verification_status"] == "unverified":
        return [f"{eid}: no verified enrichment record (generation requires a verified entity)"]
    idx = evidence_index(ent)
    errs = []
    if digest is None:
        errs.append(f"{eid}: digest missing")
    else:
        errs += [f"{eid} digest: {e.message}" for e in _validator("digest").iter_errors(digest)]
    if not slides or len(slides) != 1:
        errs.append(f"{eid}: exactly one infographic is required")
    for s in slides or []:
        errs += [f"{eid} slide: {e.message}" for e in _validator("slide").iter_errors(s)]
        u = s.get("official_url")
        if u not in ent["official_urls"]:
            errs.append(f"{eid}: official_url {u} is not one of the verified official URLs")
        if s.get("source_date"):
            errs += _date_ok(s["source_date"], u, idx, window, f"{eid} slide")
    if deck is None:
        errs.append(f"{eid}: deck missing")
    else:
        errs += [f"{eid} deck: {e.message}" for e in _validator("deck").iter_errors(deck)]
        ids = {s["id"] for s in deck.get("sources", [])}
        for sec in ("overview", "impact"):
            for r in deck.get(sec, {}).get("refs", []):
                if r not in ids:
                    errs.append(f"{eid} deck.{sec}: ref {r} does not resolve to a deck source")
        for s in deck.get("sources", []):
            if s["url"] not in idx:
                errs.append(f"{eid} deck: source {s['url']} is neither an official URL nor captured evidence")
            elif s.get("date"):
                errs += _date_ok(s["date"], s["url"], idx, window, f"{eid} deck")
    return errs


def check_batch(proposal, enrichment, window, current=None):
    """Returns (accepted_entity_ids, problems). `current` enables the diff-based change cap and deletion check."""
    keys = set(proposal["digest"]) | set(proposal["slides"]) | set(proposal["decks"])
    problems = []
    if current is not None:
        cur_keys = set(current["digest"]) | set(current["slides"]) | set(current["decks"])
        for e in sorted(cur_keys - keys):
            problems.append(f"{e}: deleted by proposal (deletions need manual review)")
        changed = [e for e in sorted(keys) if any(proposal[k].get(e) != current[k].get(e) for k in FILES)]
        if len(changed) > MAX_CHANGED_ENTITIES:
            return [], problems + [f"too many changed entities ({len(changed)} > {MAX_CHANGED_ENTITIES}); needs manual review"]
    else:
        changed = sorted(keys)
    ok = []
    for eid in changed:
        p = check_entity(eid, proposal["digest"].get(eid), proposal["slides"].get(eid), proposal["decks"].get(eid), enrichment, window)
        problems += p
        if not p:
            ok.append(eid)
    return ok, problems


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True)
    ap.add_argument("--proposal")
    ap.add_argument("--base")
    a = ap.parse_args(argv)
    wk = ROOT / "data" / "reports" / a.week
    enr = json.loads((wk / "enrichment.json").read_text(encoding="utf-8"))
    window = json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))["window"]
    proposal = load_bundle(a.proposal or wk)
    if any(v is None for v in proposal.values()):
        print("missing bundle file(s)", file=sys.stderr)
        return 2
    current = load_bundle(a.base, missing_ok=True) if a.base else None
    ok, problems = check_batch(proposal, enr, window, current)
    for p in problems:
        print("REJECT", p, file=sys.stderr)
    print(f"accepted {len(ok)} entities; {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
