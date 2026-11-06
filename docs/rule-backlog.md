# PRF Rule Backlog (v0.1)

> Candidate rules that the corpus does not cover yet. Each entry records why
> the rule is wanted, the ID prefix it would take in
> `rules/reliability-rules.yaml`, and a one-sentence draft. Nothing here is a
> rule until it lands in the YAML with detection, examples and benchmark
> references; until then no knowledge seed or benchmark case may cite it.
>
> Sources: open questions Q1, Q2 and Q4 in `docs/bench-ref-audit.md`, and the
> seeds in `knowledge/security-rules.md` §4 whose canonical column reads
> "no canonical rule (backlog)".

## Summary

| Entry | Source | Proposed prefix | Next free ID |
|---|---|---|---|
| B-1 SMB protocol configuration changes | BENCH-NET-003, Q1 | `SAFE-` | SAFE-016 |
| B-2 Generic configuration convergence (check-then-set) | BENCH-SVC-008, BENCH-SVC-009, Q2 | `IDEM-` | IDEM-016 |
| B-3 AppLocker / WDAC coexistence | KS-20 | `SEC-` | SEC-026 |
| B-4 Approval gate for identity-scope changes | KS-21 | `SAFE-` | SAFE-017 |
| B-5 No obfuscation aimed at AMSI or scanners | KS-24 | `SEC-` | SEC-027 |
| B-6 Read-only audit requests stay read-only | BENCH-AD-009, BENCH-AD-011, BENCH-AZ-009, Q4 | `SAFE-` | SAFE-018 |

The "next free ID" column assumes the entries land in table order; IDs are
assigned only when a rule is added.

## B-1 SMB protocol configuration changes

**Motivation.** BENCH-NET-003 disables SMBv1 on named file servers while SMB2/3
must stay intact, staged host by host with a revert path. No rule covers SMB
server or client configuration (`Set-SmbServerConfiguration`,
`Disable-WindowsOptionalFeature -FeatureName SMB1Protocol`), so the case is
left with only the generic pending-restart rule (SAFE-006). The failure modes
are specific: disabling SMB2 together with SMB1 (they share a switch on old
builds), fleet-wide changes with no client inventory, and feature removal
that forces an unplanned reboot.

**Proposed prefix.** `SAFE-` (execution safety: the change can cut off file
access estate-wide).

**Draft.** Change SMB protocol settings only on explicitly named hosts, after
recording the current SMB1/SMB2/SMB3 server and client state and the clients
still negotiating the protocol being removed, and verify after each host that
the remaining dialects and shares still answer before moving on.

## B-2 Generic configuration convergence (check-then-set)

**Motivation.** BENCH-SVC-008 (Data Collector Set via `logman`) and
BENCH-SVC-009 (event-log size and overflow via `Limit-EventLog`) both require
"query current state, compare, then create or update only what differs". The
IDEM series covers this per surface (registry IDEM-005, firewall IDEM-008,
environment IDEM-010, cloud tags IDEM-015) but has no rule for the general
pattern, so both cases borrowed the registry rule IDEM-005 as a stand-in (now
removed on `fix/bench-rule-refs`).

**Proposed prefix.** `IDEM-`.

**Draft.** Before writing any configuration value, read the current value
through the same interface that will set it, change only the values that
differ from the desired state, and report already-converged items as skipped
so a re-run is a no-op.

## B-3 AppLocker / WDAC coexistence (KS-20)

**Motivation.** `knowledge/security-rules.md` §3.3 and seed KS-20 describe how
generated code must behave on hosts under AppLocker or WDAC (App Control), but
no canonical rule backs the seed. The constructs it would detect, such as
copying scripts to user-writable allow-listed paths, alternate data streams,
or launching through trusted signed proxies to slip past policy, are not
covered by SEC-006 (LOLBins with foreign payloads) or SEC-022 (JEA and
constrained-language boundaries).

**Proposed prefix.** `SEC-`.

**Draft.** Never work around AppLocker or WDAC policy by relocating code into
allow-listed paths, hiding it in alternate data streams, or launching it
through trusted signed hosts; ship signed artifacts that the policy admits
and stop with an explanation when it does not.

## B-4 Approval gate for identity-scope changes (KS-21)

**Motivation.** Seed KS-21 and §3 of `knowledge/security-rules.md` require
that creating, disabling or re-scoping accounts, group membership, domain
trust or tenant-wide settings carry a recorded approval (ticket, approver,
scope, rollback) before the step can run. SAFE-013 covers OU scoping and
preview for bulk AD deletions only; it does not require the approval record,
and no rule covers Entra/M365 tenant-scope changes.

**Proposed prefix.** `SAFE-` (a change gate, like SAFE-013 and SAFE-014;
`SEC-` is the alternative if it is filed under the security pack with its
seed).

**Draft.** Emit identity, domain or tenant-scope mutations only behind an
approval block that names the ticket, approver, exact scope and rollback
step, and refuse to produce runnable code for the mutation when that block
cannot be filled.

## B-5 No obfuscation aimed at AMSI or scanners (KS-24)

**Motivation.** Seed KS-24 and §1 of `knowledge/security-rules.md` treat
scanner-evasion shapes (string chunking and concatenation, layered encoding,
character-map rebuilding, AMSI probing or patching) as a detection signal in
their own right. SEC-005 covers EncodedCommand and decode-then-execute only,
and SEC-023 covers telemetry tampering; neither covers code that is merely
written to be unreadable in a 4104 script-block log.

**Proposed prefix.** `SEC-`.

**Draft.** Write code that reads plainly in a script-block log: no
concatenated or reversed command names, character-code rebuilding, layered
encoding, or any attempt to probe, bypass or patch AMSI.

## B-6 Read-only audit requests stay read-only

**Motivation.** After the always-selected reference audit
(`docs/bench-ref-audit.md` §6, on `fix/bench-always-on-refs`), BENCH-AD-009
(mail-contact attribute scan), BENCH-AD-011 ("password never expires" report)
and BENCH-AZ-009 (scale-set instance-protection check) have empty
`related_rules`: their only references were filler COMP-001 / SEC-001 entries.
All three are "report only" requests whose negative checks are the same
failure: the agent fixes what it finds in the same run (clearing proxy
addresses, unsetting the flag domain-wide, `Update-AzVmss` set-wide), in one
case even under `-WhatIf`. No rule says that a read-only request must not
mutate; SAFE-013 and SAFE-014 gate changes that were asked for, not changes
that were not.

**Proposed prefix.** `SAFE-` (unrequested mutation is a blast-radius
failure, not a security-control bypass).

**Draft.** When a request is a report, audit or check, emit only read
cmdlets (`Get-*`, `Test-*`, exports) and keep any remediation as a separate,
clearly labelled proposal that the operator must request before it runs.
