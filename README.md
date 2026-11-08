# PowerShell Reliability Framework (PRF)

> Reliable PowerShell generation for AI agents — AI Agent Infrastructure / Windows Automation Reliability Layer
>
> v0.1.0 Skill Package (Part I of the planning proposal: Skill-based Reliability Layer)

[中文说明](docs/README.zh-CN.md)

PRF is not a tutorial, not a code generator, and not a Copilot prompt. It is a
**reliability layer** for AI coding agents: any agent that supports Agent Skills
loads PRF by default *before* generating / reviewing / executing PowerShell,
turning the flow from "LLM → script → pray" into:

```text
Probe → Classify(R/W/D/N/C) → Draft → Rule Check → Propose(-WhatIf) → Confirm → Execute → Verify → Report
```

## Repository layout

```text
PowerShell-Reliability-Framework/
├── SKILL.md                        # skill entry: Generation Protocol + hard gates
├── README.md                       # this file
├── knowledge/
│   ├── powershell-model.md         # object pipeline / streams / error semantics
│   ├── compatibility.md            # 5.1 ↔ 7.x delta matrix, module availability reality
│   ├── security-rules.md           # attack surface & defensive generation posture
│   ├── enterprise-patterns.md      # ShouldProcess, logging, remoting, bulk-op etiquette
│   ├── anti-patterns.md            # AP-01..AP-24 catalog (bad → good)
│   └── here-strings-and-heredocs.md # delimiter grammar, bash heredoc collision, writer divergence
├── rules/
│   └── reliability-rules.yaml      # machine-readable rule corpus (v0.1: 109 rules)
├── examples/
│   ├── bad/                        # 12 negative samples (NEVER execute)
│   ├── good/                       # 12 matching positive samples
│   └── EXAMPLES.md                 # pair index
├── benchmark/
│   └── cases.json                  # reliability benchmark (v0.1: 110 cases)
├── tools/
│   ├── probe-environment.ps1       # canonical target-machine probe
│   ├── validate.py                 # package integrity gate (L0)
│   └── rule-selftest.py            # detector-vs-snippet consistency gate (L1)
├── .github/workflows/ci.yml        # CI gates (macOS-first lane)
└── docs/
    ├── README.zh-CN.md             # 简体中文说明
    └── testing-plan.md             # testing & evaluation plan (A/B protocol)
```

## Quick start

1. **Hook it into your agent**: hand this directory to your agent's skill loader
   (the entry point is `SKILL.md`).
   - Claude Code / Cursor-style agents: drop it into their skills directory.
   - DeepSeek Harness (DSH): copy to `${DSH_HOME:-$HOME/.dsh}/.agent-presets/<preset>/skills/`
     or reference it from your preset composition.
2. Instruct the agent: *"Load the powershell-reliability-framework skill before any
   PowerShell work."*
3. Validate package integrity anytime:

   ```bash
   python3 tools/validate.py        # L0 gate
   python3 tools/rule-selftest.py   # L1 gate
   ```

4. Probe a target machine before generating anything against it:

   ```powershell
   pwsh -File tools/probe-environment.ps1 -AsJson   # or powershell.exe
   ```

## Rule schema

Each rule in `rules/reliability-rules.yaml` carries: `id · category · severity · title · description · bad · good · rationale · applies_to · tags · detection{pattern, psscriptanalyzer}`.
45 of 109 rules currently include detection hints (`detection_rule_count` in the YAML header); coverage grows with v0.2 static-analysis integration.

## Roadmap

| Version | Goal | Status |
|---|---|---|
| v0.1.0 | Skill-based Reliability Layer | ✅ this repository (alpha) |
| v0.2.0 | Static Analysis Integration (PSScriptAnalyzer + custom PRF rules) | `detection.psscriptanalyzer` field reserved |
| v0.3.0 | Sandbox Execution (Windows Sandbox / Hyper-V runner) | — |
| v0.4.0 | Enterprise Policy Engine (admission-controller style deny/audit/approve) | — |
| v0.5.0 | Multi-Agent Architecture (Planner/Engineer/Reviewer/Executor) | — |
| v1.0 | PowerShell Agent Runtime | Vision |

## Success metrics

| Metric | Target | Current |
|---|---:|---:|
| Benchmark cases | 100 | 110 ✅ |
| Rules | 100+ | 109 |
| Knowledge docs | 5 | 6 |
| Example pairs | — | 12 |
| Agent support | 3+ | any Skills-capable agent (portable format) |

Measured effectiveness targets (A/B protocol in `docs/testing-plan.md`) are being
established; none are claimed until the first double-blind benchmark run completes.

## Safety notice

`examples/bad/` and security-rule snippets show *attack-shaped* PowerShell
(download-and-execute cradles, persistence patterns) **as negative training
examples only**. Snippets that would switch off a security control (Defender
preferences, audit logging, inline native code, script-URL loaders) are written
as descriptions rather than runnable lines; the rest is real PowerShell, with
example hosts where a URL is needed. Never execute `examples/bad/*.ps1` or a
rule's `bad` snippet. PRF is intended exclusively for defensive and
reliability-engineering purposes.

## License

Dual licensing by artifact type:

| Content | License | Scope |
|---|---|---|
| Code — `tools/`, CI workflows | [MIT](LICENSE) | scripts and automation |
| Dataset — `knowledge/`, `rules/`, `benchmark/`, `examples/` | [CC-BY-4.0](LICENSE-DATA) | knowledge base, rule corpus, benchmark cases, paired examples |

Suggested dataset attribution: *PowerShell Reliability Framework (PRF) dataset, CC-BY-4.0.*
