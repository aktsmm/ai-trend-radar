"""Deterministic PNG build of every slide in site/data.js via headless Chromium (Playwright).

python -m render.build_png [--out build/slides]
Outputs are build artifacts (git-ignored; CI uploads them as artifacts).
"""
import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from collect.common import ROOT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build/slides")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads(re.search(r"=\s*(\{.*\});?\s*$", (ROOT / "site" / "data.js").read_text(encoding="utf-8"), re.S).group(1))
    made = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        for t in data["trends"]:
            for i in range(len(t["slides"])):
                page.goto((ROOT / "site" / "slide.html").as_uri() + f"?e={t['entity_id']}&n={i}")
                page.wait_for_selector("body[data-ready='1']")
                path = out / f"{t['entity_id']}-{i + 1}.png"
                page.locator(".slide").screenshot(path=str(path))
                made.append(path.name)
        b.close()
    print(len(made), "PNGs ->", out)


if __name__ == "__main__":
    main()
