"""Build every publishable artifact into site/ (all git-ignored build output), for the latest week AND every archived week.

latest week (root):   site/assets/slides, site/assets/summary.png, site/briefs/<id>.json (brief pages + slide XML), site/template.pptx, site/downloads/trends.json
older weeks:          site/w/<week>/{index.html,data.js,assets/...,downloads/...}
API (all weeks):      site/api/v1/...  (see render/build_api.py)

python -m render.build_site [--no-pptx]
"""
import argparse
import json
import shutil

from playwright.sync_api import sync_playwright

from analyze import weeks as W
from collect.common import ROOT
from render import build_pptx

SITE = ROOT / "site"
PDF_OPTS = dict(width="1280px", height="720px", print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})

OVERFLOW_JS = """() => [...document.querySelectorAll('.sm-th,.sm-body,.sm-left,.sm-right,.d-box,.d-card,.d-panel,.d-col,.d-body,.d-take,.d-aud,.pt,.panel,.iside,.ibody,.step')]
  .filter(e => e.scrollHeight > e.clientHeight + 1 || e.scrollWidth > e.clientWidth + 1).map(e => e.className)"""


def data_js(data):
    return "window.TRENDS = " + json.dumps(data, ensure_ascii=False) + ";\n"


def week_index_html(label):
    """The week page is the normal index with relative paths re-pointed to the site root (data.js / assets / downloads stay local)."""
    t = (SITE / "index.html").read_text(encoding="utf-8")
    for a, b in (('href="style.css"', 'href="../../style.css"'), ('src="app.js"', 'src="../../app.js"'), ('src="download.js"', 'src="../../download.js"'), ('href="archive.html"', 'href="../../archive.html"'), ('href="glossary.html"', 'href="../../glossary.html"'),
                 ('href="api/v1/index.json"', 'href="../../api/v1/index.json"'), ('href="feed.xml"', 'href="../../feed.xml"'), ('<a class="brand" href="#top">', '<a class="brand" href="../../index.html">')):
        t = t.replace(a, b)
    t = t.replace('<main class="wrap" id="top">', f'<main class="wrap" id="top">\n  <p class="stale" role="note">過去の週({label})のダイジェストです。<a href="../../index.html">最新の週へ</a> / <a href="../../archive.html">アーカイブ</a></p>', 1)
    t = t.replace("<title>AI Trend Radar", f"<title>{label} - AI Trend Radar", 1)
    return t


def slide_xmls(item, tmp):
    """The two slide XML parts of an item's editable deck (python-pptx), reused by the browser-side PPTX merge."""
    import zipfile
    build_pptx.build(item, tmp)
    with zipfile.ZipFile(tmp) as z:
        return [z.read(f"ppt/slides/slide{n}.xml").decode("utf-8") for n in (1, 2)]


def render_week(page, hq, data, out, made, overflow):
    """Render one week into `out` (the site root for the latest week). data.js must already hold this week.
    Public: infographics, week summary, and briefs/<id>.json (2 deck page JPEGs + 2 slide XMLs) used by the browser-side PDF / PPTX download."""
    import base64
    import tempfile
    from pathlib import Path

    label = data["window"]["label"]
    for d in ("assets/slides", "downloads", "briefs"):
        (out / d).mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp())
    for t in data["trends"]:
        eid = t["entity_id"]
        if t.get("slides"):
            page.goto((SITE / "slide.html").as_uri() + f"?e={eid}&n=0")
            page.wait_for_selector("body[data-ready='1']")
            overflow += [f"{label} {eid} infographic: {c}" for c in page.evaluate(OVERFLOW_JS)]
            page.locator(".slide").screenshot(path=str(out / "assets" / "slides" / f"{eid}.png"))
            made["png"] += 1
        if t.get("deck"):
            jpegs = []
            for n in (0, 1):
                hq.goto((SITE / "deck.html").as_uri() + f"?e={eid}&n={n}")
                hq.wait_for_selector("body[data-ready='1']")
                overflow += [f"{label} {eid} deck p{n + 1}: {c}" for c in hq.evaluate(OVERFLOW_JS)]
                jpegs.append(hq.locator(".dslide").screenshot(type="jpeg", quality=82))
            payload = {"id": eid, "title": (t.get("slides") or [{}])[0].get("title") or t["keyword"],
                       "pages": [base64.b64encode(j).decode("ascii") for j in jpegs], "slides": slide_xmls(t, tmpdir / f"{eid}.pptx")}
            (out / "briefs" / f"{eid}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            made["briefs"] += 1
    if W.published(data):
        page.goto((SITE / "summary.html").as_uri())
        page.wait_for_selector("body[data-ready='1']")
        overflow += [f"{label} summary: {c}" for c in page.evaluate(OVERFLOW_JS)]
        page.locator(".sm").screenshot(path=str(out / "assets" / "summary.png"))
        made["png"] += 1
    prs = build_pptx.new_prs()
    prs.save(str(out / "template.pptx"))
    (out / "downloads" / "trends.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pptx", action="store_true", help="(ignored; kept for compatibility)")
    a = ap.parse_args()
    latest = W.latest_label()
    archive = W.archive_weeks()
    for d in ("assets/slides", "assets/decks", "downloads", "briefs", "api", "w"):
        shutil.rmtree(SITE / d, ignore_errors=True)  # no stale artifacts survive a rebuild
    made = {"png": 0, "briefs": 0}
    overflow = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        hq = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1.25)
        for label, data in archive:
            out = SITE if label == latest else SITE / "w" / label
            (SITE / "data.js").write_text(data_js(data), encoding="utf-8")  # the renderers read window.TRENDS from site/data.js
            render_week(page, hq, data, out, made, overflow)
            if label != latest:
                (out / "data.js").write_text(data_js(data), encoding="utf-8")
                (out / "index.html").write_text(week_index_html(label), encoding="utf-8")
        b.close()
    latest_data = dict(archive)[latest]
    (SITE / "data.js").write_text(data_js(latest_data), encoding="utf-8")  # restore the latest week as the site's data
    from render import build_api
    build_api.main()
    print(made, "weeks:", [w for w, _ in archive])
    if overflow:
        print("OVERFLOW:", *overflow, sep="\n  ")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
