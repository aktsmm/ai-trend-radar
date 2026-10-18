"""Per-week data access for the archive: every week that has data/reports/<week>/report.json can be rebuilt with its own enrichment.

week_data(label) returns the same shape as data/trends.json (report + verification + digest/slides/deck + themes + rejected candidates).
The latest week is read from data/trends.json (the output of `python -m analyze.apply`); older weeks are re-derived from their report.json.
"""
import json

from analyze.report import apply_enrichment
from collect.common import ROOT

REPORTS = ROOT / "data" / "reports"


def latest_label():
    return json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))["window"]["label"]


def site_label():
    """The week the public site shows: the newest week with at least one published item (the pipeline week in data/trends.json can be newer
    while its digest is still being drafted / auto-merged; the site must not switch to an empty week meanwhile)."""
    latest = latest_label()
    if published(week_data(latest)):
        return latest
    for w in reversed(labels()):
        if w != latest and published(week_data(w)):
            return w
    return latest


def site_data():
    return week_data(site_label())


def labels():
    return sorted(p.name for p in REPORTS.iterdir() if (p / "report.json").exists())


def week_data(label):
    if label == latest_label():
        return json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))
    d = json.loads((REPORTS / label / "report.json").read_text(encoding="utf-8"))
    for t in d["trends"]:
        for k in ("digest", "deck"):
            t.pop(k, None)
        t["slides"] = []
    apply_enrichment(d["trends"], label)
    for name, key, default in (("themes.json", "themes", []), ("rejected_candidates.json", "rejected_candidates", {})):
        p = REPORTS / label / name
        d[key] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    return d


def published(data):
    return [t for t in data["trends"] if t.get("deck")]


def archive_weeks():
    """[(label, data)] for every week that has at least one published item, oldest first (the pipeline week is added only when nothing is published yet)."""
    out = []
    for w in labels():
        d = week_data(w)
        if published(d):
            out.append((w, d))
    return out or [(latest_label(), week_data(latest_label()))]
