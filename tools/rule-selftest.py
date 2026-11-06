#!/usr/bin/env python3
"""PRF L1 rule-consistency self-test.

For every rule carrying a detection.pattern, verifies against the rule's OWN
bad/good snippets:
  OK      pattern matches bad, not good          -> precise token detector
  WARN    pattern matches both bad and good      -> contextual detector: the
          construct appears in the compliant fix too (expected for IDEM/SAFE
          guard-rules); real gating requires AST/context analysis (v0.2)
  FAIL    inverted (good-only) or dead (neither)

Also sweeps example pairs and reports detectors that fire nowhere, and runs
fixed regression cases for detectors that once misfired:
  FAIL    a regression snippet is matched (or missed) against its expectation,
          or a pattern fires on an example file it must stay silent on

Usage: python3 tools/rule-selftest.py   (exit 0 unless FAIL entries)
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
rules = yaml.safe_load(
    (ROOT / "rules" / "reliability-rules.yaml").read_text(encoding="utf-8"))["rules"]

example_files = sorted((ROOT / "examples").rglob("*.ps1"))
example_texts = [(p.relative_to(ROOT).as_posix(), p.read_text(errors="ignore"))
                 for p in example_files]

ok, warn, fail = [], [], []
tested = 0
for r in rules:
    pat = (r.get("detection") or {}).get("pattern")
    if not pat:
        continue
    rid = r["id"]
    tested += 1
    rx = re.compile(pat)
    hit_bad = bool(rx.search(r.get("bad", "")))
    hit_good = bool(rx.search(r.get("good", "")))
    if hit_bad and not hit_good:
        ok.append(rid)
    elif hit_bad and hit_good:
        warn.append(f"{rid}: contextual detector - fires on both bad and good "
                    f"(needs context gate, see v0.2)")
    elif hit_good:
        fail.append(f"{rid}: INVERTED - fires only on the compliant snippet")
    else:
        fail.append(f"{rid}: DEAD - fires on neither snippet")

# Regression cases: (rule id, snippet, must match).  Issue #2: HD-002 fired on
# a comment that merely mentions the header (examples/good/12, line 23).
REGRESSIONS = [
    ("HD-002", "# HD-002: nothing but whitespace after @'.\n$s = @'\nbody\n'@\n", False),
    ("HD-002", "    # indented note about @'.\n", False),
    ("HD-002", "$s = @' # note\nbody\n'@\n", True),
    ("HD-002", "@'; $x = 1\n", True),
]
# Example files a pattern must not fire on.
SILENT_ON = {
    "HD-002": ["examples/good/12-heredoc-child-script-runner.ps1"],
}
patterns = {r["id"]: (r.get("detection") or {}).get("pattern") for r in rules}
texts = dict(example_texts)
regressions = 0
for rid, snippet, want in REGRESSIONS:
    regressions += 1
    got = bool(re.search(patterns[rid], snippet))
    if got != want:
        fail.append(f"{rid}: regression - {'missed' if want else 'matched'} {snippet!r}")
for rid, paths in SILENT_ON.items():
    for rel in paths:
        regressions += 1
        if re.search(patterns[rid], texts[rel]):
            fail.append(f"{rid}: regression - fires on {rel}")

cold = []
for r in rules:
    pat = (r.get("detection") or {}).get("pattern")
    if not pat:
        continue
    rx = re.compile(pat)
    ex_hits = sum(1 for _, t in example_texts if rx.search(t))
    own_hits = bool(rx.search(r.get("bad", ""))) or bool(rx.search(r.get("good", "")))
    if ex_hits == 0 and not own_hits:
        cold.append(r["id"])

print(f"pattern-bearing rules tested : {tested}")
print(f"  precise  (bad only)        : {len(ok)}")
print(f"  contextual (both sides)    : {len(warn)}")
print(f"  FAIL                       : {len(fail)}")
print(f"cold detectors (no corpus/example hit): {len(cold)} {cold}")
print(f"regression cases             : {regressions}")
if warn:
    print("\ncontextual detectors (WARN):")
    for w in warn:
        print("  ~", w)
if fail:
    print("\nFAILURES:")
    for f in fail:
        print("  x", f)
    sys.exit(1)
print("\nL1 SELF-TEST PASS")
