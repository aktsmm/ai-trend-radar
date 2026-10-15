"""Path allowlist for auto-merging data PRs created by the digest workflow.

Reads changed file paths (one per line) on stdin. Exit 0 and print the report JSON files to take from the PR when every path is allowed;
exit 1 and print the offending paths otherwise. data/trends.json and site/data.js are generated artifacts: they are allowed in the PR
but never trusted (the merge job regenerates them with trusted code and requires them to be identical).
"""
import re
import sys

REPORT = re.compile(r"^data/reports/\d{4}-W\d{2}/(enrichment|digest|slides|decks|themes|glossary|rejected_candidates)\.json$")
GENERATED = {"data/trends.json", "site/data.js"}


def classify(paths):
    take, generated, bad = [], [], []
    for p in (x.strip() for x in paths if x.strip()):
        if REPORT.match(p):
            take.append(p)
        elif p in GENERATED:
            generated.append(p)
        else:
            bad.append(p)
    return take, generated, bad


def main():
    take, generated, bad = classify(sys.stdin.read().splitlines())
    if bad or not take:
        print("\n".join(bad) or "(no report files changed)", file=sys.stderr)
        return 1
    print("\n".join(take))
    return 0


if __name__ == "__main__":
    sys.exit(main())
