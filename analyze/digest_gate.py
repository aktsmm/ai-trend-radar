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
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "trend.schema.json").read_text(encoding="utf-8"))
MAX_CHANGED_ENTITIES = 6
FILES = {"digest": "digest.json", "slides": "slides.json", "decks": "decks.json"}


SECRET_RE = re.compile(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[bp]-[A-Za-z0-9-]{10,}|"
                       r"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?i:api[_-]?key|secret|password|token)\s*[:=]\s*[A-Za-z0-9/+_-]{16,})")
HTML_RE = re.compile(r"<\s*(script|iframe|img|object|embed|style|link)\b|javascript:", re.I)


def _text_problems(eid, obj):
    blob = json.dumps(obj, ensure_ascii=False)
    out = []
    if SECRET_RE.search(blob):
        out.append(f"{eid}: secret-like string in generated text (never publish)")
    if HTML_RE.search(blob):
        out.append(f"{eid}: HTML / script markup in generated text")
    return out


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


def _lo(window):
    """Lower bound: the report window starts a week earlier for dates. A report that is regenerated later in the same week slides its rolling
    window forward, and entries published earlier (pinned) must not fail because of that."""
    y, m, d = map(int, window["from"].split("-"))
    return (date(y, m, d) - timedelta(days=7)).isoformat()


def _date_ok(d, url, idx, window, who):
    errs = []
    if not (_lo(window) <= d <= window["to"]):
        errs.append(f"{who}: date {d} is outside the report window {_lo(window)}..{window['to']}")
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
    errs = _text_problems(eid, [digest, slides, deck])
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


def check_themes(themes, enrichment, decks):
    """themes: list. Every theme must cite >=2 published entities, one signal per cited entity, and only URLs captured as evidence for those entities."""
    errs = []
    if len(themes) > 4:
        errs.append("themes: at most 4 themes per week")
    seen = set()
    for th in themes:
        who = f"theme {th.get('id', '?')}"
        errs += [f"{who}: {e.message}" for e in _validator("theme").iter_errors(th)]
        errs += _text_problems(who, th)
        if th.get("id") in seen:
            errs.append(f"{who}: duplicate id")
        seen.add(th.get("id"))
        ents = th.get("entities", [])
        for e in ents:
            if e not in decks or e not in enrichment["entities"]:
                errs.append(f"{who}: entity {e} is not a published, verified entity")
        sig = {s.get("entity") for s in th.get("signals", [])}
        if sig != set(ents):
            errs.append(f"{who}: signals must cover exactly the listed entities (missing {sorted(set(ents) - sig)}, extra {sorted(sig - set(ents))})")
        allowed = set()
        for e in ents:
            if e in enrichment["entities"]:
                allowed |= set(evidence_index(enrichment["entities"][e]))
        for u in th.get("refs", []):
            if u not in allowed:
                errs.append(f"{who}: ref {u} is not captured evidence of the listed entities")
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
    ap.add_argument("--week")
    ap.add_argument("--proposal")
    ap.add_argument("--base")
    a = ap.parse_args(argv)
    window = json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))["window"]
    a.week = a.week or window["label"]
    wk = ROOT / "data" / "reports" / a.week
    enr = json.loads((wk / "enrichment.json").read_text(encoding="utf-8"))
    proposal = load_bundle(a.proposal or wk)
    if any(v is None for v in proposal.values()):
        print("missing bundle file(s)", file=sys.stderr)
        return 2
    current = load_bundle(a.base, missing_ok=True) if a.base else None
    ok, problems = check_batch(proposal, enr, window, current)
    tp = Path(a.proposal or wk) / "themes.json"
    if tp.exists():
        problems += check_themes(json.loads(tp.read_text(encoding="utf-8")), enr, proposal["decks"])
    for p in problems:
        print("REJECT", p, file=sys.stderr)
    print(f"accepted {len(ok)} entities; {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
