"""Build every publishable artifact from data/trends.json into site/ (all git-ignored build output):
  site/assets/slides/<id>.png        public infographic (1 per keyword)
  site/assets/decks/<id>-1|2.png     page previews of the downloadable brief
  site/downloads/<id>.pdf            2-page brief (Chromium print, 1280x720 per page)
  site/downloads/<id>.pptx           editable 2-slide brief (python-pptx)
  site/downloads/trends.json         machine-readable report

python -m render.build_site [--pptx-only | --no-pptx]
"""
import argparse
import json
import shutil

from playwright.sync_api import sync_playwright

from collect.common import ROOT
from render import build_pptx

SITE = ROOT / "site"


OVERFLOW_JS = """() => [...document.querySelectorAll('.d-box,.d-card,.d-panel,.d-col,.d-body,.d-take,.d-aud,.pt,.panel,.iside,.ibody,.step')]
  .filter(e => e.scrollHeight > e.clientHeight + 1 || e.scrollWidth > e.clientWidth + 1).map(e => e.className)"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pptx", action="store_true")
    a = ap.parse_args()
    data = json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))
    for d in ("assets/slides", "assets/decks", "downloads", "api"):
        shutil.rmtree(SITE / d, ignore_errors=True)  # no stale entity artifacts survive a rebuild
    for d in ("assets/slides", "assets/decks", "downloads"):
        (SITE / d).mkdir(parents=True, exist_ok=True)
    made = {"png": 0, "deck_png": 0, "pdf": 0}
    overflow = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        for t in data["trends"]:
            eid = t["entity_id"]
            if t.get("slides"):
                page.goto((SITE / "slide.html").as_uri() + f"?e={eid}&n=0")
                page.wait_for_selector("body[data-ready='1']")
                overflow += [f"{eid} infographic: {c}" for c in page.evaluate(OVERFLOW_JS)]
                page.locator(".slide").screenshot(path=str(SITE / "assets" / "slides" / f"{eid}.png"))
                made["png"] += 1
            if t.get("deck"):
                for n in (0, 1):
                    page.goto((SITE / "deck.html").as_uri() + f"?e={eid}&n={n}")
                    page.wait_for_selector("body[data-ready='1']")
                    overflow += [f"{eid} deck p{n + 1}: {c}" for c in page.evaluate(OVERFLOW_JS)]
                    page.locator(".dslide").screenshot(path=str(SITE / "assets" / "decks" / f"{eid}-{n + 1}.png"))
                    made["deck_png"] += 1
                page.goto((SITE / "deck.html").as_uri() + f"?e={eid}&all=1")
                page.wait_for_selector("body[data-ready='1']")
                page.pdf(path=str(SITE / "downloads" / f"{eid}.pdf"), width="1280px", height="720px", print_background=True,
                         margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
                made["pdf"] += 1
        weekly = [t for t in data["trends"] if t.get("deck")]
        if weekly:
            page.goto((SITE / "deck.html").as_uri() + "?weekly=1")
            page.wait_for_selector("body[data-ready='1']")
            overflow += [f"weekly: {c}" for c in page.evaluate(OVERFLOW_JS)]
            page.pdf(path=str(SITE / "downloads" / f"weekly-{data['window']['label']}.pdf"), width="1280px", height="720px", print_background=True,
                     margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
            made["pdf"] += 1
        b.close()
    shutil.copyfile(ROOT / "data" / "trends.json", SITE / "downloads" / "trends.json")
    if not a.no_pptx:
        build_pptx.run()
    from render import build_api
    build_api.main()
    print(made)
    if overflow:
        print("OVERFLOW:", *overflow, sep="\n  ")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
