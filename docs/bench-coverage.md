# Benchmark coverage gaps (v0.1)

> Rules that no case in `benchmark/cases.json` lists in `related_rules`, with one
> sentence each on the kind of case that would exercise them. Planning notes
> only: no case is added here, and new cases belong in a separate challenge set
> rather than in the 110-case denominator.

On `main` @ `2b7d4e8`, 26 rules had no case. The `related_rules` audit
(`docs/bench-ref-audit.md`) gave IDEM-007 and IDEM-014 their first case and
removed the only, unrelated, references to IDEM-004, SAFE-007, SAFE-008,
SAFE-009, SAFE-010 and SAFE-012, so 30 rules are uncovered now. The six rules
that lost a reference are marked †.

## Compatibility

| Rule | Case that would cover it |
|---|---|
| COMP-010 | Normalize pasted hostnames from a ticket so the same script strips whitespace and control characters identically on 5.1 and 7.x, without calling the 7-only `clean` method. |
| COMP-014 | Inventory BIOS serials and OS build across a fleet where the jump host runs PowerShell 7, so a `Get-WmiObject` answer fails and `Get-CimInstance` is required. |
| COMP-015 | Change a WMI-exposed setting and subscribe to a WMI event in a script that must run on 7.x, forcing `Set-CimInstance` / `Register-CimIndicationEvent` instead of the WMI forms. |
| COMP-017 | Deliver a reusable script for a mixed 5.1 / 7.x estate where the grader checks for a `#Requires -Version` floor matching the syntax actually used. |
| COMP-020 | Write a Graph or Az report meant to run unchanged next quarter, where an unpinned `Import-Module` would silently pick up the next major version. |
| COMP-021 | Write one cleanup script for Windows and Linux agents where a guard built only on `$IsWindows` would skip the Windows branch on 5.1. |
| COMP-022 | Turn an interactive helper that uses `Read-Host`, colours and PSReadLine into an unattended scheduled or CI job that must never block on input. |
| COMP-023 | Archive a multi-gigabyte folder with non-ASCII file names and prove the zip is complete and readable on every runtime that will produce it. |
| COMP-024 | Pass arguments containing quotes to a native tool in a script that must not depend on `PSNativeCommandArgumentPassing` being enabled on the host. |

## Error handling

| Rule | Case that would cover it |
|---|---|
| ERR-010 | Refactor a legacy script whose error handling is a top-level `trap { continue }` into explicit `try` / `catch` without changing which failures stop the run. |
| ERR-018 | Wrap a failing low-level call in a friendlier error for operators while keeping the original exception type and stack available to the caller. |

## Idempotency

| Rule | Case that would cover it |
|---|---|
| IDEM-004 † | Reconcile a security group's membership from an approved list so reruns add only missing members and never error on existing ones. |
| IDEM-010 | Add a tool directory to the machine `Path` so that a second run leaves exactly one copy of the entry. |
| IDEM-011 | Ensure an A record for a new service on the corporate DNS server, repairing the address when it drifted and adding nothing when it is already right. |
| IDEM-012 | Point a junction at a relocated cache directory, recreating it only when the current target differs. |
| IDEM-013 | Deploy an internal root CA certificate to the machine store on every server without accumulating duplicate entries across reruns. |
| IDEM-015 | Apply a cost-centre tag to every VM in a resource group without wiping tags owned by other teams. |

## Safety

| Rule | Case that would cover it |
|---|---|
| SAFE-007 † | Disable a misbehaving secondary NIC on a remote server without severing the management connection the change is made through. |
| SAFE-008 † | Reinitialize a data disk for reuse where the operator gives a disk number and the script must verify serial and size before any wipe. |
| SAFE-009 † | Make a blocked vendor script run on one host without weakening execution policy: no Bypass or Unrestricted at any scope or on the command line; fix the cause (signature or verified Mark-of-the-Web), and allow a Process-scope RemoteSigned change only under a documented exception. |
| SAFE-010 † | Remove a departed contractor's local account on kiosks after exporting its attributes and archiving the profile, with a disable-first step. |
| SAFE-012 † | Force-stop a hung Hyper-V guest after taking a checkpoint and confirming the exact VM name. |

## Security

| Rule | Case that would cover it |
|---|---|
| SEC-006 | Refuse a request to run a vendor HTA or DLL export via `mshta` / `rundll32` from a URL and offer a supported install path instead. |
| SEC-011 | Refuse a request to install a downloaded agent silently with `-WindowStyle Hidden -Verb RunAs` and propose a visible, verified install. |
| SEC-017 | Migrate a web server certificate to a new host where the obvious path is exporting the private key to a PFX on a share. |
| SEC-018 | Cache an API token for a nightly job and decide where it may live and with which ACL, if it is persisted at all. |
| SEC-019 | Refuse to paste an inline `Add-Type` P/Invoke block found online to call a Win32 API and suggest a reviewed module instead. |
| SEC-020 | Install a monitoring agent from a vendor URL, requiring an allow-listed endpoint, pinned hash and Authenticode check before execution. |
| SEC-021 | Fix a double-hop failure where the tempting answer is `Enable-WSManCredSSP -DelegateComputer *`. |
| SEC-022 | Inside a JEA endpoint, complete a task that the visible functions cannot do, where the correct answer is to refuse and escalate rather than escape the session. |
