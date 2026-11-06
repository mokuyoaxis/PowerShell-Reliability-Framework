# PRF Example Pairs — Index

This directory holds the paired training corpus for the PowerShell Reliability
Framework (PRF) v0.1.0. Each pair teaches one reliability lesson twice: a
`bad/<nn>-<slug>.ps1` file shows the compact, plausible, tempting output an AI
agent tends to produce, and the identically named `good/<nn>-<slug>.ps1` shows
the compliant rewrite whose inline comments name the exact PRF rule ids it
satisfies (e.g. `# SEC-002: verify SHA256 before execution`). The bad files are
deliberately realistic — that is what makes them useful for comparison — and
they are never meant to be executed.

| Pair | Theme | Key rules | Risk |
|------|-------|-----------|------|
| 01 | download-execute-cradle | SEC-002, SEC-003, SEC-010 | critical |
| 02 | wildcard-delete-logs | SAFE-001, SAFE-002 | high |
| 03 | registry-service-startup-ensure | IDEM-005, SAFE-011 | medium |
| 04 | service-retry-restart | ERR-013, ERR-001 | medium |
| 05 | ad-bulk-disable-ou | SAFE-013, ERR-001 | high |
| 06 | azure-stop-vms-by-tag | SAFE-015 | high |
| 07 | firewall-rule-ensure | IDEM-008 | medium |
| 08 | scheduled-task-register | IDEM-009, SEC-010 | medium |
| 09 | plaintext-credential-export | SEC-014 | critical |
| 10 | foreach-parallel-compat | COMP-001 | low |
| 11 | heredoc-manifest-writer | HD-004, HD-009 | medium |
| 12 | heredoc-child-script-runner | HD-001, HD-002, SEC-001 | high |

SEC-010 in pairs 01 and 08 is shown by the good file only: it checks the
Authenticode signature and runs under the existing execution policy instead of
passing `-ExecutionPolicy Bypass`.

## How agents should use these pairs

1. **Draft** — write your PowerShell solution for the task at hand as you
   normally would, before consulting any example.
2. **Compare against a pair** — pick the pair whose theme matches your draft's
   riskiest operation (remote execution, deletion, bulk identity or cloud
   changes, credentials, idempotent resource creation, version-sensitive
   syntax). Read the bad file first and check honestly whether your draft
   contains its anti-pattern; then read the good file and note which rule ids
   your draft is missing.
3. **Self-review** — revise your draft until it satisfies every rule id named
   in that good file's inline comments: guards read state before writing,
   destructive steps preview with `-WhatIf` and use precise scoping, errors are
   terminating inside `try`/`catch` with bounded retries, secrets stay out of
   files, and edition-specific features are gated on `$PSVersionTable`. Only
   then present the final script.

**WARNING:** `bad/*.ps1` files are NEGATIVE training examples. Never execute
them — not even "just to see". Several depict genuinely dangerous behavior
(remote cradles, unscoped deletions, plaintext credential dumps), and executing
them would cause real harm.
