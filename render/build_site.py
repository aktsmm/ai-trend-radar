"""Build every publishable artifact into site/ (all git-ignored build output), for the latest week AND every archived week.

latest week (root):   site/assets/slides|decks, site/downloads/*.pdf|*.pptx|weekly-<w>.*, site/index.html
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

OVERFLOW_JS = """() => [...document.querySelectorAll('.d-box,.d-card,.d-panel,.d-col,.d-body,.d-take,.d-aud,.pt,.panel,.iside,.ibody,.step')]
  .filter(e => e.scrollHeight > e.clientHeight + 1 || e.scrollWidth > e.clientWidth + 1).map(e => e.className)"""


def data_js(data):
    return "window.TRENDS = " + json.dumps(data, ensure_ascii=False) + ";\n"


def week_index_html(label):
    """The week page is the normal index with relative paths re-pointed to the site root (data.js / assets / downloads stay local)."""
    t = (SITE / "index.html").read_text(encoding="utf-8")
    for a, b in (('href="style.css"', 'href="../../style.css"'), ('src="app.js"', 'src="../../app.js"'), ('href="archive.html"', 'href="../../archive.html"'),
                 ('href="api/v1/index.json"', 'href="../../api/v1/index.json"'), ('href="feed.xml"', 'href="../../feed.xml"'), ('<a class="brand" href="#top">', '<a class="brand" href="../../index.html">')):
        t = t.replace(a, b)
    t = t.replace('<main class="wrap" id="top">', f'<main class="wrap" id="top">\n  <p class="stale" role="note">過去の週({label})のダイジェストです。<a href="../../index.html">最新の週へ</a> / <a href="../../archive.html">アーカイブ</a></p>', 1)
    t = t.replace("<title>AI Trend Radar", f"<title>{label} - AI Trend Radar", 1)
    return t


def render_week(page, data, out, made, overflow, no_pptx):
    """Render the infographics / briefs of one week into `out` (the site root for the latest week). data.js must already hold this week."""
    label = data["window"]["label"]
    for d in ("assets/slides", "assets/decks", "downloads"):
        (out / d).mkdir(parents=True, exist_ok=True)
    for t in data["trends"]:
        eid = t["entity_id"]
        if t.get("slides"):
            page.goto((SITE / "slide.html").as_uri() + f"?e={eid}&n=0")
            page.wait_for_selector("body[data-ready='1']")
            overflow += [f"{label} {eid} infographic: {c}" for c in page.evaluate(OVERFLOW_JS)]
            page.locator(".slide").screenshot(path=str(out / "assets" / "slides" / f"{eid}.png"))
            made["png"] += 1
        if t.get("deck"):
            for n in (0, 1):
                page.goto((SITE / "deck.html").as_uri() + f"?e={eid}&n={n}")
                page.wait_for_selector("body[data-ready='1']")
                overflow += [f"{label} {eid} deck p{n + 1}: {c}" for c in page.evaluate(OVERFLOW_JS)]
                page.locator(".dslide").screenshot(path=str(out / "assets" / "decks" / f"{eid}-{n + 1}.png"))
                made["deck_png"] += 1
            page.goto((SITE / "deck.html").as_uri() + f"?e={eid}&all=1")
            page.wait_for_selector("body[data-ready='1']")
            page.pdf(path=str(out / "downloads" / f"{eid}.pdf"), **PDF_OPTS)
            made["pdf"] += 1
    if W.published(data):
        page.goto((SITE / "deck.html").as_uri() + "?weekly=1")
        page.wait_for_selector("body[data-ready='1']")
        overflow += [f"{label} weekly: {c}" for c in page.evaluate(OVERFLOW_JS)]
        page.pdf(path=str(out / "downloads" / f"weekly-{label}.pdf"), **PDF_OPTS)
        made["pdf"] += 1
    (out / "downloads" / "trends.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    if not no_pptx:
        build_pptx.run(str((out / "downloads").relative_to(ROOT)), data=data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pptx", action="store_true")
    a = ap.parse_args()
    latest = W.latest_label()
    archive = W.archive_weeks()
    for d in ("assets/slides", "assets/decks", "downloads", "api", "w"):
        shutil.rmtree(SITE / d, ignore_errors=True)  # no stale artifacts survive a rebuild
    made = {"png": 0, "deck_png": 0, "pdf": 0}
    overflow = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        for label, data in archive:
            out = SITE if label == latest else SITE / "w" / label
            (SITE / "data.js").write_text(data_js(data), encoding="utf-8")  # the renderers read window.TRENDS from site/data.js
            render_week(page, data, out, made, overflow, a.no_pptx)
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
