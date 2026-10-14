"""Validate data/trends.json against schema/trend.schema.json (needs `pip install jsonschema`)."""
import json
import sys

from jsonschema import Draft202012Validator, FormatChecker

from collect.common import ROOT


def main():
    schema = json.loads((ROOT / "schema" / "trend.schema.json").read_text(encoding="utf-8"))
    data = json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8"))
    errs = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data), key=lambda e: list(e.path))
    for e in errs:
        print("INVALID", "/".join(map(str, e.path)), e.message[:160])
    print("OK" if not errs else f"{len(errs)} errors", f"({len(data['trends'])} trends)")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
