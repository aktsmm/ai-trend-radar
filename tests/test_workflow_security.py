"""Plain workflows must not put untrusted values into run: scripts, and may only use first-party actions.

Generated gh-aw *.lock.yml files are excluded (they are produced by the compiler)."""
import re
import unittest
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent / ".github" / "workflows"
UNTRUSTED = re.compile(r"\$\{\{[^}]*\b(?:github\.event\.|github\.head_ref|inputs\.)[^}]*\}\}")
RUN = re.compile(r"^(\s*)(?:-\s+)?run:\s*(.*)$")
USES = re.compile(r"^\s*(?:-\s+)?uses:\s*([^\s#]+)")


def problems(name, text):
    out, run_indent = [], -1
    for no, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        indent = len(line) - len(line.lstrip())
        if run_indent >= 0 and line.strip() and indent <= run_indent:
            run_indent = -1
        m = RUN.match(line)
        if m:
            run_indent = len(m.group(1)) + (2 if line.lstrip().startswith("- ") else 0)
            if UNTRUSTED.search(m.group(2)):
                out.append(f"{name}:{no} puts an untrusted value into a run: line; pass it through env:")
            continue
        if run_indent >= 0 and UNTRUSTED.search(line):
            out.append(f"{name}:{no} puts an untrusted value into a run: script; pass it through env:")
        u = USES.match(line)
        if u and not u.group(1).startswith("./") and not re.match(r"(actions|github)/", u.group(1)):
            out.append(f"{name}:{no} uses a third-party action ({u.group(1)})")
    return out


class WorkflowSecurityTest(unittest.TestCase):
    def test_auto_merge_cannot_swallow_a_failed_validation(self):
        # the Actions shell is `bash -e` without pipefail: `validate | tee && ok=1` and a later PIPESTATUS read always gave ok=1,
        # so a PR whose build reported OVERFLOW (or a failing test) was still merged
        text = (DIR / "auto-merge-digest.yml").read_text(encoding="utf-8")
        self.assertNotIn("PIPESTATUS", text)
        self.assertNotRegex(text, r"validate\s+2>&1\s*\|\s*tee")
        self.assertRegex(text, r"if validate > /tmp/validate\.log 2>&1; then ok=1; else ok=0; fi")

    def test_workflows_are_clean(self):
        found = []
        for f in sorted(DIR.glob("*.yml")):
            if not f.name.endswith(".lock.yml"):
                found += problems(f.name, f.read_text(encoding="utf-8"))
        self.assertEqual(found, [], "\n".join(found))

    def test_guard_detects_both_risks(self):
        sample = 'steps:\n  - run: |\n      echo "${{ github.event.issue.title }}"\n  - uses: someone/action@v1\n'
        self.assertEqual(len(problems("x.yml", sample)), 2)


if __name__ == "__main__":
    unittest.main()
