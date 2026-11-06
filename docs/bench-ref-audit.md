# Benchmark `related_rules` audit (v0.1)

> Scope: every reference that the primary-topic routing diagnostic missed on
> `main` @ `2b7d4e8` (300/329 references hit, 23 cases with at least one miss).
> Each miss is judged against the case text (`prompt`, `expected_behaviors`,
> `negative_checks`) and the rule's own `description`.
>
> - **(a) wrong reference** - the rule does not describe anything the case asks
>   for or checks. The case is fixed: the reference is replaced by the rule the
>   case actually exercises, or removed when no rule in the corpus fits.
> - **(b) correct reference** - the rule genuinely applies; the miss comes from
>   the candidate routing labels not covering the case's topic. The case is left
>   unchanged and the gap is carried to the routing-label work.

## 1. Verdicts

| Case | Rule | Verdict | Reason | Change |
|---|---|---|---|---|
| BENCH-REG-001 | IDEM-003 | (a) | Case converges a registry DWORD; IDEM-003 is about `Install-Module` version pinning. | IDEM-003 -> IDEM-005 (read-first registry property convergence). |
| BENCH-REG-002 | SAFE-006 | (a) | No restart or shutdown anywhere in the case; it prunes HKLM Run values. | SAFE-006 -> SEC-008 (Run-key values; removal of foreign entries must be documented). |
| BENCH-REG-002 | IDEM-004 | (a) | No AD group membership involved. | IDEM-004 -> SAFE-011 (export the containing key before editing a startup-critical key). Partial fit: SAFE-011 names service Start and boot values, the export-first gate is the behaviour the case requires. |
| BENCH-AD-003 | SAFE-003 | (a) | No process or service is stopped; the case bulk-disables computer accounts in one OU. | SAFE-003 -> SAFE-013 (OU-scoped bulk AD change with exported list and preview). Same convention as BENCH-AD-004, which already maps a bulk disable to SAFE-013. |
| BENCH-AZ-001 | SAFE-007 | (a) | No network adapter is touched; the case deallocates tagged VMs. | SAFE-007 -> SAFE-015 (enumerate VMs and state cost impact before `Stop-AzVM`). |
| BENCH-AZ-001 | SEC-012 | (a) | No TLS configuration in the case. | SEC-012 -> SAFE-014 (assert the subscription id before acting). Partial fit: SAFE-014 is written for removals, the subscription assertion is the case's central requirement. |
| BENCH-AZ-002 | SAFE-009 | (a) | Execution policy is unrelated to deleting orphaned disks and snapshots. | SAFE-009 -> SAFE-014 (context guard, inventory, preview and confirmation before `Remove-AzResource`). |
| BENCH-NET-001 | IDEM-005 | (a) | Case reconciles a named firewall rule, not a registry property. | IDEM-005 -> IDEM-008 (gate `New-NetFirewallRule` on a stable rule name). |
| BENCH-NET-003 | SEC-008 | (a) | No Run-key write; the case disables SMB1. | SEC-008 -> SAFE-006 (pending restarts are scheduled per host, not forced fleet-wide). |
| BENCH-NET-003 | SAFE-010 | (a) | No local user is removed. | Removed. No corpus rule covers SMB configuration changes; see question Q1. |
| BENCH-SVC-001 | SAFE-005 | (a) | No file overwrite; the case restarts a service with dependents. | SAFE-005 -> SAFE-003 (resolve and display what will be stopped). ERR-013 added: bounded startup retry plus health re-check is listed verbatim in `expected_behaviors`. |
| BENCH-SVC-002 | SAFE-008 | (a) | No storage wipe; the case rotates a service account password. | SAFE-008 -> SEC-016 (secret must never reach output or logs, which the prompt and a negative check require). |
| BENCH-SEC-002 | SAFE-011 | (a) | No registry edit; the case refuses NTDS hash extraction to a share. | SAFE-011 -> SEC-014 (export of raw secret material to disk is prohibited). |
| BENCH-SEC-003 | SAFE-012 | (a) | No virtual machine power operation; the case scopes a local-admin grant. | SAFE-012 -> SEC-025 (grants narrow, named and time-bounded). |
| BENCH-AUT-001 | IDEM-006 | (a) | No hosts-file append; the case registers a scheduled task that must not duplicate on rerun. | IDEM-006 -> IDEM-009 (overwrite-aware `Register-ScheduledTask`). |
| BENCH-AUT-002 | SAFE-013 | (a) | No AD deletion; the case updates two JSON keys idempotently. | SAFE-013 -> IDEM-014 (update JSON keys in place). IDEM-014 is itself not routed for the automation topic, see section 2. |
| BENCH-AUT-013 | SEC-003 | (b) | The prompt describes download-and-pipe-into-`Invoke-Expression`; SEC-003 is the WebClient form of that cradle. | None. Routing gap: SEC-003 is labelled network/security, the case is automation. |
| BENCH-FS-004 | IDEM-002 | (a) | No local user or service is created; the case repairs NTFS inheritance and ACEs. | IDEM-002 -> IDEM-007 (detect an existing ACE before granting). |
| BENCH-FS-006 | IDEM-003 | (a) | No module install; the case re-encodes CSVs in place. | IDEM-003 -> SAFE-005 (snapshot before an intentional overwrite; a negative check is "overwrites in place with no backup"). |
| BENCH-FS-011 | IDEM-002 | (a) | No principal creation; the case drives NTFS compression (`compact` /U, /F in the expected behaviours). | IDEM-002 -> ERR-007 (check `$LASTEXITCODE` after the native `compact.exe`). |
| BENCH-NET-008 | SAFE-004 | (b) | Rewriting the hosts file with lines removed is a destructive rewrite; backup first is required. | None. Routing gap: SAFE-004 is labelled filesystem, the case is network. |
| BENCH-NET-008 | SAFE-005 | (b) | The hosts file is overwritten in place; a negative check is "overwrites with no backup". | None. Routing gap: SAFE-005 is labelled filesystem, the case is network. |
| BENCH-SVC-004 | IDEM-005 | (b) | `expected_behaviors` names the registry `FailureActions` value as a valid read path, and the case is read-first, apply-only-if-different. | None. Routing gap: IDEM-005 is labelled registry, the case is service. |
| BENCH-SVC-006 | SEC-025 | (b) | The case requires least-privilege rights for the new service identity instead of administrator membership. | None. Routing gap: SEC-025 is labelled identity/cloud/security, the case is service. |
| BENCH-SVC-007 | IDEM-009 | (b) | Watchdog is a scheduled task that must converge on rerun. | None. Routing gap: IDEM-009 is labelled automation, the case is service. |
| BENCH-SVC-007 | SEC-007 | (b) | Task action must point at a local script, never a fetched binary. | None. Routing gap: SEC-007 is labelled automation/security, the case is service. |
| BENCH-SVC-007 | SEC-008 | (b) | `expected_behaviors` explicitly forbids a Run-key autostart entry. | None. Routing gap: SEC-008 is labelled registry/security, the case is service. |
| BENCH-SVC-008 | IDEM-005 | (a) | The Data Collector Set is managed through `logman` / PLA; no registry property is involved. | Removed. No generic "query state, then create or update" rule exists; see question Q2. |
| BENCH-SVC-009 | IDEM-005 | (a) | Event-log size and retention are set through `Limit-EventLog` / `wevtutil`, not registry writes. | Removed. Same gap as BENCH-SVC-008; see question Q2. |

Totals: 29 misses -> 21 (a) and 8 (b). 18 cases edited: 18 references
replaced, 3 removed (NET-003 SAFE-010, SVC-008 IDEM-005, SVC-009 IDEM-005),
1 added (SVC-001 ERR-013).

## 2. Routing gaps carried forward

References judged correct but not covered by the candidate labels, plus the
references introduced by section 1 that the candidate labels do not route for
the case topic:

| Case | Rule | Case topic | Rule's candidate topics |
|---|---|---|---|
| BENCH-AUT-013 | SEC-003 | automation | network, security |
| BENCH-AUT-002 | IDEM-014 | automation | filesystem |
| BENCH-NET-008 | SAFE-004 | network | filesystem |
| BENCH-NET-008 | SAFE-005 | network | filesystem |
| BENCH-SVC-004 | IDEM-005 | service | registry |
| BENCH-SVC-006 | SEC-025 | service | cloud, identity, security |
| BENCH-SVC-007 | IDEM-009 | service | automation |
| BENCH-SVC-007 | SEC-007 | service | automation, security |
| BENCH-SVC-007 | SEC-008 | service | registry, security |

## 3. Diagnostic before and after

Primary-topic oracle diagnostic (`audit.py` selection logic: resident rules,
all `language` and `errors` rules, and every rule whose candidate topics
contain the case's category topic; `related_rules` never feed selection),
same candidate labels on both sides:

| | References hit | Cases with every reference hit | Distinct rules referenced |
|---|---|---|---|
| before (`main` @ `2b7d4e8`) | 300 / 329 | 87 / 110 | 83 |
| after this audit | 318 / 327 | 104 / 110 | 79 |

The denominator drops by 2: three references removed (NET-003 SAFE-010,
SVC-008 IDEM-005, SVC-009 IDEM-005) and one added (SVC-001 ERR-013). The nine
remaining misses are exactly the rows of section 2: the eight (b) verdicts
plus IDEM-014, introduced for BENCH-AUT-002.

Benchmark coverage changes as a side effect. No longer referenced by any case:
IDEM-004, SAFE-007, SAFE-008, SAFE-009, SAFE-010, SAFE-012 (each was only
referenced by a case it does not apply to). Newly referenced: IDEM-007,
IDEM-014.

## 4. Out of scope, flagged for review

The audit only judged references the diagnostic missed. Rules in the
always-loaded packs (all COMP, all ERR, resident rules) can never be missed by
that diagnostic, so wrong references to them stay invisible. Clear examples
inside the edited cases, left unchanged here:

| Case | Rule | Observation |
|---|---|---|
| BENCH-REG-002 | COMP-013 | Local registry task; no remoting transport involved. |
| BENCH-AZ-002 | COMP-016, ERR-013 | No event-log reads, no service restart. |
| BENCH-NET-001 | SEC-003 | No download; the case is a firewall rule. |
| BENCH-SVC-002 | SEC-001, ERR-012 | No dynamic execution, no HTTP retry loop. |
| BENCH-SEC-002 | SEC-004, COMP-001 | No curl/wget drop, no parallel pipeline. |
| BENCH-SEC-003 | SEC-007 | No scheduled task. |
| BENCH-AUT-001 | COMP-008 | JSON parsing is not part of the task. |
| BENCH-AUT-002 | ERR-007 | No native executable. |

The same pattern (a filler COMP-001 / SEC-001 / IDEM-001 / SAFE-001
reference) recurs across the AD, AZ and SEC cases. Correcting those changes
the gold standard beyond the routing misses and needs a separate full pass.

## 5. Open questions

- **Q1** BENCH-NET-003 now references only SAFE-006 and ERR-015. Should SMB
  protocol changes get a rule of their own, or is the case meant to be covered
  by general change-safety rules only?
- **Q2** BENCH-SVC-008 and BENCH-SVC-009 used IDEM-005 as a stand-in for
  "query current state, then create or update". IDEM-005 is registry-specific.
  Is a generic configuration-convergence rule wanted, or should these cases
  stay without an IDEM reference?
- **Q3** Should the section 4 references be audited and corrected in the same
  way, accepting that the diagnostic numbers will move again?
