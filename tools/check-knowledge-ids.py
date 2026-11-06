#!/usr/bin/env python3
"""PRF knowledge cross-reference gate (L0, offline).

Canonical rule IDs live only in rules/reliability-rules.yaml (three-digit,
e.g. SEC-014). Knowledge chapters keep their own local seed numbering in a
separate namespace so a seed can never be read as a rule ID:

  KS-NN   knowledge/security-rules.md   seed table (section 4)
  KC-NN   knowledge/compatibility.md    seed table (chapter head)
  AP-NN   knowledge/anti-patterns.md    catalog headings

Gates:
  1. canonical  - rule ids in the YAML are unique
  2. seeds      - every seed namespace is defined once, unique and contiguous
                  from 01; its canonical column resolves to real rule ids
  3. references - every canonical ref (COMP|SAFE|IDEM|SEC|ERR|HD-NNN) and every
                  seed ref (KS|KC|AP-NN) in SKILL.md, knowledge/ and
                  examples/EXAMPLES.md resolves
  4. legacy     - no short-form rule ids (COMP-01, SEC-1) and no truncated
                  refs such as "(SEC-013, COMP-)"; series lists like
                  "Related: COMP-, SAFE-" stay legal

Usage: python3 tools/check-knowledge-ids.py   (exit 0 = PASS, 1 = FAIL)
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
errors = []


def err(msg: str) -> None:
    errors.append(msg)


PREFIXES = "COMP|SAFE|IDEM|SEC|ERR|HD"
CANON_REF = re.compile(rf"\b(?:{PREFIXES})-\d{{3}}\b")
SHORT_REF = re.compile(rf"\b(?:{PREFIXES})-(?:\d{{1,2}}|\d{{4,}})\b")
TRUNCATED = re.compile(rf"\b(?:{PREFIXES}|KS|KC|AP)-(?=\))")
SEED_REF = re.compile(r"\b(KS|KC|AP)-(\d+)\b")

# -------------------------------------------------------------- canonical --
rules = yaml.safe_load(
    (ROOT / "rules" / "reliability-rules.yaml").read_text(encoding="utf-8"))["rules"]
rule_ids = [str(r.get("id")) for r in rules]
canon = set(rule_ids)
for rid in sorted({i for i in rule_ids if rule_ids.count(i) > 1}):
    err(f"duplicate rule id in reliability-rules.yaml: {rid}")

# ------------------------------------------------------------------ seeds --
SEED_SOURCES = {
    "KS": ("knowledge/security-rules.md", re.compile(r"^\| (KS-\d{2}) \|(.*)\|\s*$", re.M)),
    "KC": ("knowledge/compatibility.md", re.compile(r"^\| (KC-\d{2}) \|(.*)\|\s*$", re.M)),
    "AP": ("knowledge/anti-patterns.md", re.compile(r"^#{2,3} (AP-\d{2}) \S()", re.M)),
}
seeds = {}
for ns, (rel, rx) in SEED_SOURCES.items():
    text = (ROOT / rel).read_text(encoding="utf-8")
    found = rx.findall(text)
    ids = [sid for sid, _ in found]
    if not ids:
        err(f"{rel}: no {ns}- seed definitions found")
        continue
    for sid in sorted({i for i in ids if ids.count(i) > 1}):
        err(f"{rel}: seed {sid} defined more than once")
    nums = sorted(int(i.split("-")[1]) for i in set(ids))
    if nums != list(range(1, len(nums) + 1)):
        err(f"{rel}: {ns}- seeds are not contiguous from 01: {nums}")
    seeds[ns] = set(ids)
    for sid, row in found:
        for ref in CANON_REF.findall(row):
            if ref not in canon:
                err(f"{rel}: seed {sid} maps to unknown rule {ref}")

# ------------------------------------------------------------- references --
SCANNED = [ROOT / "SKILL.md", ROOT / "examples" / "EXAMPLES.md"]
SCANNED += sorted((ROOT / "knowledge").glob("*.md"))
ref_count = 0
for p in SCANNED:
    rel = p.relative_to(ROOT).as_posix()
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        for ref in CANON_REF.findall(line):
            ref_count += 1
            if ref not in canon:
                err(f"{rel}:{n}: unknown rule {ref}")
        for ns, num in SEED_REF.findall(line):
            ref_count += 1
            sid = f"{ns}-{num}"
            if len(num) != 2 or sid not in seeds.get(ns, set()):
                err(f"{rel}:{n}: unknown seed {sid}")
        for ref in SHORT_REF.findall(line):
            err(f"{rel}:{n}: short-form id {ref} is not a rule id")
        if TRUNCATED.search(line):
            err(f"{rel}:{n}: truncated reference: {line.strip()[:80]}")

# ---------------------------------------------------------------- summary --
print(f"rules: {len(canon)} | seeds: " +
      ", ".join(f"{ns} {len(v)}" for ns, v in sorted(seeds.items())) +
      f" | references checked: {ref_count} in {len(SCANNED)} files")
if errors:
    print(f"\nFAIL - {len(errors)} issue(s):")
    for e in errors:
        print("  x", e)
    sys.exit(1)
print("\nPASS: knowledge ids are unique and every reference resolves.")
