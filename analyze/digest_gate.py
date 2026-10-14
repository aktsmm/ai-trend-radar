"""Gate for LLM-generated digest/infographic JSON (Phase 3 / plan A). No LLM call here: this only decides whether a generated
proposal is allowed to be written to data/reports/<week>/{digest,slides}.json.

Checks: JSON Schema, URLs restricted to the entity's verified official URLs, source_date inside the report window,
and a cap on how many entities one run may change. Anything else is rejected, never auto-merged.
"""
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "trend.schema.json").read_text(encoding="utf-8"))
MAX_CHANGED_ENTITIES = 6


def _validator(name):
    return Draft202012Validator({"$ref": f"#/$defs/{name}", "$defs": SCHEMA["$defs"]}, format_checker=FormatChecker())


def check_entity(eid, digest, slides, enrichment, window):
    """Return a list of problems (empty list = acceptable)."""
    errs = []
    ent = enrichment["entities"].get(eid)
    if not ent or ent["verification_status"] == "unverified":
        return [f"{eid}: no verified enrichment record (generation requires a verified entity)"]
    errs += [f"{eid} digest: {e.message}" for e in _validator("digest").iter_errors(digest)]
    if len(slides) != 1:
        errs.append(f"{eid}: exactly one infographic is required")
    allowed = set(ent["official_urls"])
    for s in slides:
        errs += [f"{eid} slide: {e.message}" for e in _validator("slide").iter_errors(s)]
        if s.get("official_url") not in allowed:
            errs.append(f"{eid}: official_url {s.get('official_url')} is not one of the verified official URLs")
        d = s.get("source_date")
        if d and not (window["from"] <= d <= window["to"]):
            errs.append(f"{eid}: source_date {d} is outside the report window {window['from']}..{window['to']}")
    return errs


def check_batch(proposal, enrichment, window, current):
    """proposal / current: {"digest": {eid: ...}, "slides": {eid: [...]}}. Returns (accepted_entity_ids, problems)."""
    changed = [e for e in proposal["digest"] if proposal["digest"][e] != current["digest"].get(e)
               or proposal["slides"].get(e) != current["slides"].get(e)]
    problems = []
    if len(changed) > MAX_CHANGED_ENTITIES:
        problems.append(f"too many changed entities ({len(changed)} > {MAX_CHANGED_ENTITIES}); needs manual review")
        return [], problems
    ok = []
    for eid in changed:
        p = check_entity(eid, proposal["digest"][eid], proposal["slides"].get(eid, []), enrichment, window)
        problems += p
        if not p:
            ok.append(eid)
    return ok, problems
