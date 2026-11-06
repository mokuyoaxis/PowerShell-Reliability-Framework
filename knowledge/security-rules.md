# Security Rules

> **PowerShell Reliability Framework (PRF)** · `knowledge/security-rules.md` · v0.1.0
> Audience: LLM coding agents and their developers. Scope: PowerShell generated for Windows
> enterprise automation — domain-joined servers, endpoint fleets, and Entra/M365 tenants.

Generated PowerShell is a security artifact whether or not its author intended it to be. These
rules define the posture agents MUST apply when emitting PowerShell in enterprise contexts.
Rule seeds are indexed in the final table (`KS-01` … `KS-25`). Seed numbers are local to this
document and are not rule IDs; each seed names the canonical rule(s) in
`rules/reliability-rules.yaml` that implement it. Companion rule series are
referenced throughout: `ERR-` (error architecture), `SAFE-` (safe execution), `IDEM-`
(idempotency), and `COMP-` (Windows PowerShell 5.1 / PowerShell 7.x compatibility).

---

## 1. Threat model — generated code is attack surface *and* audit liability

Two facts shape every rule below.

**Fact 1: the shortest path to "it worked" overlaps with attacker tradecraft.** Large language
models learned PowerShell substantially from forums, paste sites, and Q&A threads where the
celebrated answers to "how do I run/install/deploy this?" are frequently LOLBAS-shaped:
dynamic string execution, download-and-execute one-liners, encoded commands, and
living-off-the-land binaries coerced into running foreign payloads. An agent optimizing for a
first-try success will rediscover malware mechanics unprompted. The output is not exotic; it
is a help-desk script whose *shape* is indistinguishable from a commodity loader.

**Fact 2: defenders triage by shape, and AI noise destroys signal.** Enterprise defenders see
PowerShell through two instruments, and generated code must treat both as first-class readers:

- **AMSI (Antimalware Scan Interface).** On Windows, Windows PowerShell 5.1+ and PowerShell
  7.x submit script content to the registered antivirus provider at execution time. Content
  engineered to evade scanning — chunked concatenation, runtime decoding, character-map tricks
  — is itself among the highest-fidelity detection signals available to defenders. Generated
  code must never attempt to defeat, probe, or reason around AMSI (KS-24).
- **Script Block Logging.** PowerShell records decompiled script blocks at execution time
  (event ID 4104, `Microsoft-Windows-PowerShell/Operational`), including code that was
  assembled dynamically at runtime. Hiding logic inside `Invoke-Expression` therefore fails
  twice: it is flagged as suspicious, *and* it still lands in the log in readable form. The
  bar for generated code is simple: it must read cleanly inside a 4104 event.

Industry and academic work on malicious PowerShell delivery chains — dropper campaigns,
obfuscated download cradles, staged loaders; the problem space studied generically by research
in the PowerDrive tradition — has converged on one durable conclusion: the *shape* of
fetch → decode → execute is reliably fingerprintable by static analyzers and behavioral
detection alike, independent of the payload it carries. PRF adopts the generative corollary:
agents must refuse to emit that shape at all rather than emit it "cleanly." No specific
publication is cited or required; the design rule stands on its own.

Finally, generated code is an **audit liability**. When incident responders pull six months of
4104 events and find thousands of machine-authored one-off scripts with no ticket, no owner,
and no signature, every legitimate operation becomes expensive to defend after the fact.
Auditability — attribution, approval trail, reviewable source — is therefore a generation-time
requirement, not an operations afterthought (KS-21, KS-22).

---

## 2. Dangerous primitives — deny by default

Each row names a primitive that appears constantly in AI-generated PowerShell, the typical way
a model reaches for it, and the defensive replacement the agent must emit instead. Denying the
primitive alone is insufficient — the replacement is the rule (KS-01 through KS-18).

| Primitive | Typical AI-generated usage | Defensive replacement |
|---|---|---|
| `Invoke-Expression` / `iex` alias | Building commands from interpolated strings; config-driven dispatch; "flexible" wrappers around user input | Pre-parsed constructs only: explicit calls, `switch` maps, hashtable dispatch to known functions; validate external values against an allow-list before use (KS-01) |
| `& $commandString`, `. $scriptText` | Same intent in operator form, common when the model wants "late binding" | Bind early: resolve the exact cmdlet or function name at authoring time; pass data as parameters, never as code |
| `[scriptblock]::Create($code)` | Synthesizing logic at runtime from templates or API responses | Ship the scriptblock as literal source in the file; if variability is needed, parameterize data, not code (KS-01) |
| Download cradles: `(iwr $u).Content \| iex`, `(New-Object Net.WebClient).DownloadString($u)` piped into execution, `curl.exe -o $env:TEMP\t.ps1; t.ps1` | One-line tool installation; bootstrapping helpers from gists or internal shares | Download to a managed path, verify a pinned SHA-256 hash or Authenticode signature, then invoke a documented entry point; prefer native package management (`winget`, MSI) (KS-02, KS-03) |
| `-EncodedCommand`; base64-decode-execute | "Avoiding quoting problems"; concealing long bootstrap commands | Encode *data*, never *code*: pass arguments via files or arrays; if bootstrap logic is genuinely complex, ship a signed script (KS-04) |
| `mshta`, `rundll32`, `regsvr32` with foreign arguments | Launching HTA payloads, calling exotic DLL exports, registering proxies | Use supported front-door tooling; these binaries are acceptable only invoking first-party, signed, documented payloads — never fetched or temp-path content (KS-05) |
| Persistence creation: `Register-ScheduledTask` pointing at foreign binaries; `Set-ItemProperty HKCU:\…\Run` writes | "Keep my agent alive"; self-healing loops | Persist only version-controlled, signed scripts under managed paths with a named owning team, and treat each registration as an approved change (KS-06) |
| `Set-MpPreference` / `Add-MpPreference -Exclusion*` tampering | Making an antivirus false positive "go away" mid-deployment | Forbidden in generated automation; route through the security exception process. Exclusion writes are treated as adversary-in-use behavior (KS-07) |
| `Set-ExecutionPolicy Bypass` / `Unrestricted` as workaround | Fixing "this script won't run" on a target host | Preserve GPO-held policy: Authenticode-sign the script, deploy to a trusted path under RemoteSigned, or use an approved context — never widen machine-scope policy (KS-08) |
| Plaintext credentials: `-Password (ConvertTo-SecureString 'P@ss' -AsPlainText -Force)`; passwords on command lines | Quick service-account auth; "test first, secure later" (never revisited) | Retrieve credentials from SecretManagement-backed vaults (KS-09); confine plaintext conversion to fixtures with synthetic values (KS-10); keep secrets off command lines, which leak via process enumeration (KS-11) |
| Private-key export: `Export-PfxCertificate` of exportable keys to flat files | Certificate migration and backup scripts | Keys stay non-exportable by default; export requires key-custodian approval, AES-256 PFX encryption, and out-of-band passphrase handoff (KS-12) |
| TLS downgrade: `[Net.ServicePointManager]::SecurityProtocol = 'Tls'` and enum hacks forcing legacy protocols | Rescuing calls against legacy internal endpoints | Raise, never lower: the single sanctioned 5.1-era line enables `Tls12` alongside existing defaults; 7.x needs no hack; legacy servers get fixed server-side (KS-13) |
| Validation suppression: `ServerCertificateValidationCallback = { $true }`; reflexive `-SkipCertificateCheck` | Making self-signed dev endpoints work | Repair trust instead: import the issuing root CA, fix SAN/name mismatches. Any `-SkipCertificateCheck` needs inline justification and is barred from production paths (KS-14, KS-15) |
| Hidden-window `Start-Process` of downloaded binaries | Launching installers or fetched tools quietly | Observable execution by default: installation flows through the software-deployment system or a verified package; hidden launches of foreign binaries require written justification (KS-17, KS-18) |

---

## 3. Generation-time defenses

### 3.1 Allow-list mindset over blocklists

Blocklists rot: the model invents a fourth spelling of the thing you banned. Generate only
from a positive vocabulary — approved modules, an approved .NET surface, approved parameter
shapes — and stop with a clarifying question when a task appears to require something
off-list such as raw reflection, `Add-Type` compilation, or undocumented COM objects. A
generator that can only say yes to known-good shapes is far easier to audit than one that
merely avoids a moving blacklist.

### 3.2 Constrained Language Mode and JEA role capabilities

Assume target sessions may run under **Constrained Language Mode**, which restricts scripts to
core cmdlets plus a subset of .NET, or under **JEA** role capabilities, which expose exactly
the whitelisted cmdlets — often with per-parameter validation — through ephemeral virtual
accounts. Design consequences:

- Emit no `Add-Type`, arbitrary static .NET, or COM instantiation by default; guard richer
  paths behind explicit capability checks and state the assumption in the script header.
- Never probe or attempt to escape language mode; `$ExecutionContext.SessionState.LanguageMode`
  is diagnostic context for humans, not something a script should branch around (KS-19).
- Prefer cmdlet verbs JEA authors typically expose: `Get-*` discovery, `Set-*` with validated
  parameters, and `Invoke-Command` against registered session configurations.

### 3.3 AppLocker / WDAC coexistence

Enterprises increasingly enforce application control so that only signed or path-trusted
script content runs. Generated deliverables must therefore arrive as signable artifacts with
stable paths, not as heredocs pasted into consoles. Never emit code that relocates scripts to
"allowed" paths to dodge rules, abuses alternate data streams, or uses trusted processes as
proxies: that is evasion behavior (KS-20), and it breaks under enforcement anyway.

### 3.4 Secret hygiene

Secrets enter scripts only through SecretManagement vault providers — SecretStore locally, or
Entra / Key Vault-backed extensions for shared estates:

```powershell
# The only sanctioned credential flow (KS-09)
Import-Module Microsoft.PowerShell.SecretManagement
$cred = Get-Secret -Name 'Contoso/SqlAgent'      # stored as PSCredential
Invoke-SqlMaintenance -Credential $cred
```

Corollaries: never echo secrets, including "temporarily for debugging"; scrub transcripts,
because `Start-Transcript` records whatever reached the host, so a secret printed once is
retained in plaintext; redact before writing errors, since ErrorRecords propagate into logs;
treat any secret observed by a log or terminal as burned and rotate it (KS-11).

### 3.5 Egress pinning and the TLS floor

Outbound destinations are pinned: URLs come from configuration constants or approved parameter
sets, never from untrusted input, and the endpoint list is documented beside the script
(KS-16). The protocol floor is TLS 1.2+ everywhere. The one sanctioned compatibility line —
needed only for Windows PowerShell 5.1 on older stacks — *raises* the floor:

```powershell
# PS 5.1 only; PS 7.x negotiates modern TLS by default
[Net.ServicePointManager]::SecurityProtocol =
    [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
```

Any line that narrows protocol selection below the platform default is denied (KS-13), and
any callback or switch that skips certificate validation is denied outside a reviewed
exception (KS-14, KS-15).

### 3.6 Audit trail expectations

Assume production code will be interrogated later: transcripts may be running, script-block
logging will capture every block, and reviewers will ask who ran this and why. Therefore: no
`Clear-Host` in automation, no log deletion, no silencing errors into `$null`, structured
progress messages instead of cryptic one-liners (the `ERR-` series), and an Authenticode
signature applied before distribution — signing is a release step, not an option (KS-22,
KS-23).

### 3.7 Human-approval gates for identity and tenant-scale operations

Operations touching identity or estate-wide scope — creating or disabling accounts, group
membership at scale, conditional-access or mailbox policy, DNS/DHCP changes, CA issuance, and
persistence registration — must be emitted with an approval placeholder: ticket ID, approver,
scope, and rollback note filled in before the step may run (KS-21). An agent that cannot
attribute a change to an approving human does not produce runnable code for it; it produces a
change-plan document instead.

---

## 4. Rule seeds — KS-01 … KS-25

Posture in one line: **deny dynamic execution, deny cradles, gate identity ops, demand
verification and auditability.**

| Seed | Rule seed | Canonical rules |
|---|---|---|
| KS-01 | Deny runtime synthesis/execution of code strings: `Invoke-Expression`, `iex`, `& $str`, `. $str`, `[scriptblock]::Create` on non-literal input | SEC-001 |
| KS-02 | Deny fetch-and-execute chains (download piped or redirected straight into execution) in any spelling | SEC-002, SEC-003, SEC-004 |
| KS-03 | Downloads land on managed paths and verify a pinned SHA-256 hash or Authenticode signature before any use | SEC-004, SEC-020 |
| KS-04 | Deny `-EncodedCommand` and base64/hex decode-execute of code; transport encoding wraps data only | SEC-005 |
| KS-05 | Deny LOLBin invocation (`mshta`, `rundll32`, `regsvr32`, `installutil`) with foreign scripts, paths, or DLLs | SEC-006 |
| KS-06 | Persistence objects (tasks, Run keys, services, WMI subscriptions) must target signed, owned, version-controlled payloads and require change approval | SEC-007, SEC-008 |
| KS-07 | Deny Defender/antivirus setting changes (including exclusions) outside an approved security exception record | SEC-009 |
| KS-08 | Deny widening `Set-ExecutionPolicy` (Bypass/Unrestricted at machine or user scope); fix signing and deployment instead | SEC-010 |
| KS-09 | Credentials originate from SecretManagement-backed vaults; hard-coded or file-borne secrets are denied | SEC-014 |
| KS-10 | `ConvertTo-SecureString -AsPlainText -Force` permitted only in fixtures with obviously synthetic values, never production paths | SEC-014 |
| KS-11 | Secrets never reach command lines, host output, transcripts, or ErrorRecords; observed secrets are rotated | SEC-015, SEC-016 |
| KS-12 | Private-key export is non-default: requires custodian approval, AES-256 PFX, out-of-band passphrase delivery | SEC-017 |
| KS-13 | Enforce a TLS 1.2+ floor; downgrading protocol selection below platform defaults is denied | SEC-012 |
| KS-14 | Certificate trust failures are repaired (root CA import, SAN/name fixes), never suppressed | SEC-013 |
| KS-15 | `-SkipCertificateCheck` or validation-returning-`$true` callbacks require inline reviewed justification and are barred from production paths | SEC-013 |
| KS-16 | Pin egress: endpoints come from documented allow-lists; URLs derived from untrusted input are denied | SEC-024 |
| KS-17 | Deny executing freshly downloaded binaries directly; installation flows through verified packages or documented installers | SEC-020 |
| KS-18 | Stealth UI flags (hidden windows, suppressed consoles) on foreign binaries require written justification; default is observable execution | SEC-011 |
| KS-19 | Default emission must function under Constrained Language Mode; FullLanguage assumptions are stated and checked | SEC-022 |
| KS-20 | Coexist with AppLocker/WDAC: no path games, stream tricks, or trusted-proxy abuse; distribute signed artifacts | no canonical rule (backlog) |
| KS-21 | Identity/domain/tenant-scope mutations require recorded human approval (ticket, approver, scope, rollback) before execution | no canonical rule (backlog) |
| KS-22 | Production runs leave an audit trail: no console clearing, no log deletion, attribution preserved in logs and output | SEC-023 |
| KS-23 | Deny disabling or tampering with telemetry (ETW, transcription, script-block logging, EDR agents) for convenience | SEC-023 |
| KS-24 | Deny obfuscation aimed at scanners or AMSI (concat-chunking, encoding layers, charmaps); code must read plainly in 4104 events | no canonical rule (backlog) |
| KS-25 | Destructive/bulk operations verify preconditions (existence, scope match, backup taken) and honor `-WhatIf`; unverifiable bulk actions block pending dry-run evidence | SAFE-001, SAFE-013, SAFE-014 |

Cross-references: surfacing denials follows the `ERR-` series (fail loudly, enrich records);
execution-safety framing is the `SAFE-` series; repeat-run stability is the `IDEM-` series;
and every 5.1/7.x delta called out above is tracked in the `COMP-` series.
