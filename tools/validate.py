#!/usr/bin/env python3
"""PRF package validator (L0 integrity gate).

Gates:
  1. structure   - knowledge docs, SKILL.md, example index present & non-trivial
  2. rule schema - required fields, unique ids, prefix/category/severity contracts,
                   uniform detection mapping ({pattern?, psscriptanalyzer?}), real
                   PSScriptAnalyzer ids only, patterns compile
  3. vocabulary  - applies_to frozen to known tokens; no duplicate titles;
                   no dangling rule-id references inside the corpus
  4. benchmark   - strict JSON, id<->category agreement, related_rules resolve,
                   rubric criterion_id uniqueness, positive rubric weights
  5. examples    - bad/good 1:1 pairing; banner rule refs resolve
  6. language    - agent-facing files are CJK-free (docs/ and README exempt)
  7. routing     - rules/routing-labels.yaml labels every rule exactly once, in
                   corpus order; risk/topics drawn from the frozen vocabularies;
                   depends_on resolves; resident count matches; rules_blob
                   matches the current rule corpus

Usage: python3 tools/validate.py   (exit 0 = PASS, 1 = FAIL)
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []


def err(msg: str) -> None:
    errors.append(msg)


KNOWN_PSA = {
    "PSAvoidAssignmentToAutomaticVariable", "PSAvoidDefaultValueForMandatoryParameter",
    "PSAvoidDefaultValueSwitchParameter", "PSAvoidGlobalAliases", "PSAvoidGlobalFunctions",
    "PSAvoidGlobalVariables", "PSAvoidLongLines", "PSAvoidOverwritingBuiltInCmdlets",
    "PSAvoidTrailingWhitespace", "PSAvoidUsingBrokenHashAlgorithms",
    "PSAvoidUsingCmdletAliases", "PSAvoidUsingComputerNameHardcoded",
    "PSAvoidUsingConvertToSecureStringWithPlainText", "PSAvoidUsingDeprecatedManifestFields",
    "PSAvoidUsingDoubleQuotesForConstantString", "PSAvoidUsingEmptyCatchBlock",
    "PSAvoidUsingInvokeExpression", "PSAvoidUsingPlainTextForPassword",
    "PSAvoidUsingPositionalParameters", "PSAvoidUsingUsernameAndPasswordArguments",
    "PSAvoidUsingWMICmdlet", "PSAvoidUsingWriteHost", "PSPossibleIncorrectComparisonWithNull",
    "PSPossibleIncorrectUsageOfAssignmentOperator", "PSPossibleIncorrectUsageOfInnerVariable",
    "PSPossibleIncorrectUsageOfRedirectionOperator", "PSUseApprovedVerbs",
    "PSUseBOMForUnicodeEncodedFile", "PSUseCmdletCorrectly", "PSUseCompatibleCmdlets",
    "PSUseCompatibleCommands", "PSUseCompatibleParameters", "PSUseCompatibleSyntax",
    "PSUseDeclaredVarsMoreThanAssignments", "PSUseLiteralInitializerForHashtable",
    "PSUseOutputTypeCorrectly", "PSUsePSCredentialType",
    "PSUseShouldProcessForStateChangingFunctions", "PSUseToExportFieldsInManifest",
    "PSUseUTF8EncodingForHelpFile",
}
APPLIES_VOCAB = {"powershell-5.1", "powershell-7"}
PREFIX_CATEGORY = {"COMP": "compatibility", "SAFE": "safety", "IDEM": "idempotency",
                   "SEC": "security", "ERR": "error-handling", "HD": "heredoc"}
BENCH_CAT = {"FS": "file-system", "REG": "registry", "AD": "active-directory",
             "AZ": "azure", "NET": "network", "SVC": "service", "SEC": "security",
             "AUT": "automation", "HD": "heredoc"}
VALID_SEVERITY = {"critical", "high", "medium", "low", "info"}
RULE_REF = re.compile(r"\b(?:COMP|SAFE|IDEM|SEC|ERR|HD)-\d{3}\b")
CJK = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff]")

# ---------------------------------------------------------------- structure --
for name in ("powershell-model", "compatibility", "security-rules",
             "enterprise-patterns", "anti-patterns", "here-strings-and-heredocs"):
    p = ROOT / "knowledge" / f"{name}.md"
    if not p.exists() or p.stat().st_size < 2000:
        err(f"missing/thin knowledge doc: {p.relative_to(ROOT)}")
if not (ROOT / "SKILL.md").exists():
    err("SKILL.md missing")
elif "Generation Protocol" not in (ROOT / "SKILL.md").read_text(encoding="utf-8"):
    err("SKILL.md does not contain 'Generation Protocol'")
if not (ROOT / "examples" / "EXAMPLES.md").exists():
    err("examples/EXAMPLES.md index missing")

lic = (ROOT / "LICENSE").read_text(encoding="utf-8", errors="ignore") \
    if (ROOT / "LICENSE").exists() else ""
if "MIT License" not in lic:
    err("LICENSE missing or does not state the MIT License")
dlic = (ROOT / "LICENSE-DATA").read_text(encoding="utf-8", errors="ignore") \
    if (ROOT / "LICENSE-DATA").exists() else ""
if "CC-BY-4.0" not in dlic:
    err("LICENSE-DATA missing or does not state CC-BY-4.0")

# -------------------------------------------------------------------- rules --
try:
    import yaml
except ImportError:
    yaml = None
    print("NOTE: pyyaml not installed - YAML gates skipped")

rule_ids, category_counts = [], {}
det_count = 0
doc = None
corpus_ids = set()  # hoisted so gates degrade gracefully without pyyaml
if yaml is not None:
    try:
        doc = yaml.safe_load((ROOT / "rules" / "reliability-rules.yaml").read_text(encoding="utf-8"))
    except Exception as exc:
        err(f"reliability-rules.yaml failed to parse: {exc}")
    if isinstance(doc, dict):
        rules = doc.get("rules") or []
        declared, declared_det = doc.get("rule_count"), doc.get("detection_rule_count")
        required = {"id", "category", "severity", "title", "description", "bad", "good"}
        titles = []
        for r in rules:
            if not isinstance(r, dict):
                err("non-object rule entry")
                continue
            rid = str(r.get("id", "<no-id>"))
            prefix = rid.split("-")[0]
            missing = required - set(r)
            if missing:
                err(f"{rid}: missing fields {sorted(missing)}")
            if rid in rule_ids:
                err(f"duplicate rule id: {rid}")
            rule_ids.append(rid)
            if prefix not in PREFIX_CATEGORY:
                err(f"{rid}: unexpected id prefix")
            else:
                if r.get("category") != PREFIX_CATEGORY[prefix]:
                    err(f"{rid}: category {r.get('category')!r} inconsistent with prefix")
                category_counts[r["category"]] = category_counts.get(r["category"], 0) + 1
            if r.get("severity") not in VALID_SEVERITY:
                err(f"{rid}: bad severity {r.get('severity')!r}")
            titles.append(str(r.get("title", "")).strip().lower())
            unknown_applies = set(r.get("applies_to") or []) - APPLIES_VOCAB
            if unknown_applies:
                err(f"{rid}: applies_to outside frozen vocab: {sorted(unknown_applies)}")

            det = r.get("detection")
            if det is None:
                continue
            det_count += 1
            if not isinstance(det, dict):
                err(f"{rid}: detection must be a mapping, got {type(det).__name__}")
                continue
            extra = set(det) - {"pattern", "psscriptanalyzer"}
            if extra:
                err(f"{rid}: detection has unknown keys {sorted(extra)}")
            if not det.get("pattern") and not det.get("psscriptanalyzer"):
                err(f"{rid}: detection is empty")
            psa = det.get("psscriptanalyzer")
            if isinstance(psa, str) and psa not in KNOWN_PSA:
                err(f"{rid}: unverified/fabricated psscriptanalyzer id: {psa}")
            pat = det.get("pattern")
            if isinstance(pat, str):
                try:
                    re.compile(pat)
                except re.error as exc:
                    err(f"{rid}: detection.pattern does not compile: {exc}")
        dup_titles = sorted({t for t in titles if titles.count(t) > 1})
        if dup_titles:
            err(f"duplicate rule titles: {dup_titles[:5]}")
        corpus_ids = set(rule_ids)
        dangling = [(str(r.get('id')), m) for r in doc.get("rules", [])
                    for m in RULE_REF.findall(
                        (r.get("description") or "") + " " + (r.get("rationale") or ""))
                    if m not in corpus_ids]
        for rid, m in dangling:
            err(f"{rid}: description/rationale references unknown rule {m}")
        if declared is not None and declared != len(rules):
            err(f"header rule_count={declared} but corpus has {len(rules)}")
        if declared_det is not None and declared_det != det_count:
            err(f"header detection_rule_count={declared_det} but found {det_count}")
        if len(rule_ids) < 100:
            err(f"expected >=100 rules, found {len(rule_ids)}")

# ---------------------------------------------------------------- benchmark --
bench = None
try:
    bench = json.loads((ROOT / "benchmark" / "cases.json").read_text(encoding="utf-8"))
except Exception as exc:
    err(f"cases.json failed to parse: {exc}")
case_ids, case_dist = [], {}
if isinstance(bench, dict):
    idpat = re.compile(r"^BENCH-(FS|REG|AD|AZ|NET|SVC|SEC|AUT|HD)-\d{3}$")
    for c in bench.get("cases", []):
        cid = str(c.get("id", "<no-id>"))
        for key in ("category", "prompt", "rubric", "expected_behaviors"):
            if key not in c:
                err(f"{cid}: missing benchmark field {key!r}")
        if cid in case_ids:
            err(f"duplicate benchmark id: {cid}")
        case_ids.append(cid)
        m = idpat.match(cid)
        if not m or BENCH_CAT.get(m.group(1)) != c.get("category"):
            err(f"{cid}: id suffix disagrees with category {c.get('category')!r}")
        cat = c.get("category", "?")
        case_dist[cat] = case_dist.get(cat, 0) + 1
        crit_ids = [i.get("criterion_id") for i in c.get("rubric", [])]
        if len(crit_ids) != len(set(crit_ids)):
            err(f"{cid}: duplicate rubric criterion_id")
        if sum(i.get("weight", 0) for i in c.get("rubric", [])) <= 0:
            err(f"{cid}: rubric has no positive weight")
        for rr in c.get("related_rules", []):
            if rr not in corpus_ids:
                err(f"{cid}: related_rules references unknown rule {rr}")
    if len(case_ids) < 20:
        err(f"expected >=20 benchmark cases, found {len(case_ids)}")

# ----------------------------------------------------------------- examples --
def slugs(folder: Path) -> set:
    return {p.name.split("-", 1)[1] for p in folder.glob("*.ps1")}


bad_slugs = slugs(ROOT / "examples" / "bad")
good_slugs = slugs(ROOT / "examples" / "good")
for orphan in sorted(bad_slugs ^ good_slugs):
    err(f"unpaired example slug: {orphan}")
if not bad_slugs:
    err("no example pairs found")

banner = re.compile(r"#\s*Rules demonstrated:\s*(.+)")
for f in sorted((ROOT / "examples").rglob("*.ps1")):
    m = banner.search(f.read_text(errors="ignore"))
    if not m:
        err(f"{f.relative_to(ROOT)}: banner missing 'Rules demonstrated' line")
        continue
    for tok in filter(None, (t.strip() for t in re.split(r"[,;\s]+", m.group(1)))):
        if tok.startswith(("COMP", "SAFE", "IDEM", "SEC", "ERR", "HD")) and tok not in corpus_ids:
            err(f"{f.relative_to(ROOT)}: banner references unknown rule {tok}")

# ------------------------------------------------------------------ routing --
RISK_VOCAB = ["R", "W", "D", "N", "C"]
TOPIC_VOCAB = ["language", "errors", "filesystem", "registry", "identity", "cloud",
               "network", "service", "automation", "security", "transport"]
labels_path = ROOT / "rules" / "routing-labels.yaml"
label_count = 0
if yaml is not None and not labels_path.exists():
    err("rules/routing-labels.yaml missing")
elif yaml is not None:
    try:
        ldoc = yaml.safe_load(labels_path.read_text(encoding="utf-8"))
    except Exception as exc:
        ldoc = None
        err(f"routing-labels.yaml failed to parse: {exc}")
    if isinstance(ldoc, dict):
        raw = (ROOT / "rules" / "reliability-rules.yaml").read_bytes().replace(b"\r\n", b"\n")
        blob = hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()
        if ldoc.get("rules_blob") != blob:
            err(f"routing-labels.yaml rules_blob {ldoc.get('rules_blob')} does not match "
                f"reliability-rules.yaml ({blob}); re-review labels against the corpus")
        if ldoc.get("risk_vocabulary") != RISK_VOCAB:
            err("routing-labels.yaml risk_vocabulary drifted from the frozen set")
        if ldoc.get("topic_vocabulary") != TOPIC_VOCAB:
            err("routing-labels.yaml topic_vocabulary drifted from the frozen set")
        entries = ldoc.get("rules") or []
        label_ids = [str(e.get("id")) if isinstance(e, dict) else "<non-object>" for e in entries]
        label_count = len(label_ids)
        if label_ids != rule_ids:
            missing = sorted(set(rule_ids) - set(label_ids))
            extra = sorted(set(label_ids) - set(rule_ids))
            dup = sorted({i for i in label_ids if label_ids.count(i) > 1})
            err(f"routing labels must cover every rule once in corpus order "
                f"(missing {missing[:5]}, unknown {extra[:5]}, duplicate {dup[:5]})")
        resident = 0
        for e in entries:
            if not isinstance(e, dict):
                continue
            lid = str(e.get("id"))
            keys = set(e) - {"id"}
            if keys != {"risk", "topics", "depends_on", "resident"}:
                err(f"{lid}: routing label keys {sorted(keys)} != "
                    f"['depends_on', 'resident', 'risk', 'topics']")
            for field, vocab in (("risk", RISK_VOCAB), ("topics", TOPIC_VOCAB)):
                vals = e.get(field)
                if not isinstance(vals, list) or not vals:
                    err(f"{lid}: {field} must be a non-empty list")
                    continue
                bad = [v for v in vals if v not in vocab]
                if bad:
                    err(f"{lid}: {field} outside frozen vocab: {bad}")
                if len(vals) != len(set(vals)):
                    err(f"{lid}: duplicate {field} values")
            deps = e.get("depends_on")
            if not isinstance(deps, list):
                err(f"{lid}: depends_on must be a list")
            else:
                for d in deps:
                    if d == lid:
                        err(f"{lid}: depends_on references itself")
                    elif d not in corpus_ids:
                        err(f"{lid}: depends_on references unknown rule {d}")
            if not isinstance(e.get("resident"), bool):
                err(f"{lid}: resident must be true or false")
            elif e["resident"]:
                resident += 1
        if ldoc.get("resident_count") != resident:
            err(f"header resident_count={ldoc.get('resident_count')} but {resident} "
                f"labels are resident")

# ----------------------------------------------------------------- language --
AGENT_FACING = [ROOT / "SKILL.md"]
AGENT_FACING += sorted((ROOT / "knowledge").glob("*.md"))
AGENT_FACING += sorted((ROOT / "rules").glob("*.yaml"))
AGENT_FACING += [ROOT / "benchmark" / "cases.json"]
AGENT_FACING += sorted((ROOT / "examples").rglob("*"))
for p in AGENT_FACING:
    if p.is_file() and CJK.search(p.read_text(encoding="utf-8", errors="ignore")):
        err(f"CJK characters found in agent-facing file: {p.relative_to(ROOT)}")

# ------------------------------------------------------------------ summary --
print(f"rules: {len(rule_ids)} {category_counts} | with detection: {det_count}")
print(f"benchmark cases: {len(case_ids)} {case_dist}")
print(f"example pairs: {len(bad_slugs)}")
print(f"routing labels: {label_count}")
if errors:
    print(f"\nFAIL - {len(errors)} issue(s):")
    for e in errors:
        print("  x", e)
    sys.exit(1)
print("\nPASS: PRF package structure is consistent.")
