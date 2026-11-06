# Security-rule conflicts in rules and knowledge (v0.1)

> Draft for review. Where a safety rule, a knowledge chapter or an anti-pattern
> repair contradicts a security rule, the security rule wins and the other
> text is rewritten to agree with it. Base: `main` @ `c3da46c`, which already
> carries the KC-/AP- renumbering and `rules/routing-labels.yaml`.

## 1. Execution policy: SAFE-009 and KC prose vs SEC-010

**Conflict.** SEC-010 says Bypass and Unrestricted are never used to make a
script run; its `bad` block lists both `Set-ExecutionPolicy -Scope Process
Bypass` and `powershell.exe -ExecutionPolicy Bypass -File`. SAFE-009 told the
agent to *prefer* `-ExecutionPolicy Bypass` on the interpreter command line,
and `knowledge/compatibility.md` §5 recommended either form as the repair. An
agent loading both rules gets opposite instructions for the same request.

**Change.**

| File | Before | After |
|---|---|---|
| `rules/reliability-rules.yaml` SAFE-009 | Title "scope to Process with justification"; description prefers per-invocation `-ExecutionPolicy Bypass`; `good` opens with `pwsh -ExecutionPolicy Bypass -File`. | Title "fix the cause instead"; description forbids Bypass and Unrestricted at any scope and on the command line, citing SEC-010, and keeps the Process-scope RemoteSigned change for a documented platform-owner exception. The per-invocation Bypass moves to `bad`; `good` checks the Authenticode signature and runs under the existing policy. Rationale updated to match. |
| `knowledge/compatibility.md` §5 | "invoke with `pwsh -ExecutionPolicy Bypass -File tool.ps1` or use `Set-ExecutionPolicy -Scope Process Bypass` inside the session" | Never repair policy by weakening it at any scope or on the command line (SEC-010, SAFE-009); sign the script or clear a verified Mark-of-the-Web with `Unblock-File`. |
| `knowledge/anti-patterns.md` AP-22 repair | `pwsh -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1; Unblock-File .\setup.ps1` | Refuse to run unless `Get-AuthenticodeSignature` reports `Valid`, then run under the existing policy. |

**This changes SAFE-009's semantics.** Before, SAFE-009 permitted (and
preferred) a per-invocation Bypass and only objected to persistent,
machine-wide loosening. After, SAFE-009 forbids every Bypass/Unrestricted
form, and the only policy change it allows is Process-scope RemoteSigned
under a recorded exception. Any benchmark scoring, routing label or example
that relied on the old reading of SAFE-009 has to be re-checked against the
new one. No benchmark case references SAFE-009 on `main` @ `c3da46c` (the
only former reference, BENCH-AZ-002, was replaced in the benchmark reference
audit), so no case depends on the old wording.

SEC-010's `good` example signs and runs the script; SAFE-009's exception path
(`Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`) is not a
weakening under SEC-010 ("keep RemoteSigned or stricter"), so the two rules no
longer disagree.

## 2. AP-11 repair vs SEC-015

**Conflict.** AP-11 (hardcoded passwords) repaired the bad example by reading
the secret from the vault and then passing
`$cred.GetNetworkCredential().Password` to `net.exe use` as an argument. SEC-015
forbids passwords on native command lines: the plaintext is visible in process
listings, CIM command-line capture and EDR telemetry the moment `net.exe`
starts.

**Change.** The repair maps the share with
`New-PSDrive -PSProvider FileSystem -Root \\file01\backup -Credential $cred`,
so the secret stays inside a credential object and never reaches argv. No
rule semantics change.

## 3. Good examples

`examples/good/01-download-execute-cradle.ps1` and
`examples/good/08-scheduled-task-register.ps1` ran their payloads with
`-ExecutionPolicy Bypass`, the pattern SEC-010 lists as `bad`. Both now follow
the new SAFE-009:

| Example | Before | After |
|---|---|---|
| 01 download-execute-cradle | `& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer` after the SHA256 check | `Get-AuthenticodeSignature` on the downloaded installer, throw unless `Status` is `Valid`, then `& powershell.exe -NoProfile -File $installer` under the existing policy. |
| 08 scheduled-task-register | Task action `-NoProfile -ExecutionPolicy Bypass -File` | `Get-AuthenticodeSignature` on the action script before registering, throw unless `Valid`; task action `-NoProfile -File`. |

Both stay Windows PowerShell 5.1 compatible and pass the L3 parse and
PSScriptAnalyzer gates. The matching `bad` examples and `examples/EXAMPLES.md`
do not mention execution policy, so they are unchanged.

## 4. Routing labels (`rules_blob`)

Editing SAFE-009 changes the git blob id of `rules/reliability-rules.yaml`
from `d00c978cd694ca5a29258c006a1cc8e43c62171c` to
`ebce76203722b5cafdda2e67ff8c0dd6517014c3`. `rules/routing-labels.yaml` is
refreshed to the new id in the same change. SAFE-009 keeps its risk and topic
labels (the rule still concerns execution policy and still depends on
SEC-010), and `review_status` stays `candidate`.
