"""Single entry point: re-apply enrichment, run the gate, (optionally) re-check URLs, build every artifact.

python -m render.build_all [--offline]     # --offline skips the URL reachability check
Order matters: apply -> digest_gate -> verify_urls -> apply (url_checks) -> build_site (PNG/PDF/PPTX/API, overflow check).
"""
import argparse
import subprocess
import sys


def sh(*mod):
    print("\n$ python -m", *mod, flush=True)
    r = subprocess.run([sys.executable, "-m", *mod])
    if r.returncode:
        raise SystemExit(r.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--week")
    a = ap.parse_args()
    import json
    from collect.common import ROOT
    week = a.week or json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))["window"]["label"]
    sh("analyze.apply")
    sh("analyze.digest_gate", "--week", week)
    if not a.offline:
        sh("render.verify_urls", "--week", week)
        sh("analyze.apply")
    sh("analyze.validate")
    sh("render.build_site")


if __name__ == "__main__":
    main()
