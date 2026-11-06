# Enterprise Patterns

> **PowerShell Reliability Framework (PRF)** · v0.1.0 · Audience: LLM coding agents generating
> PowerShell for Windows enterprise estates; accurate for Windows PowerShell 5.1 and 7.x
> unless a `COMP-` note says otherwise.

Enterprise PowerShell fails differently from laptop scripts: unattended, against shared state,
at scale, audited afterward. These patterns are the emission templates agents should
reproduce; they pair with `security-rules.md` (`SEC-*`) and the `ERR-`/`SAFE-`/`IDEM-`/
`COMP-` series.
## 1. Anatomy of an advanced function

Every emitted function is an *advanced function* — `[CmdletBinding()]` plus full parameter
attributes — never a bare `param()` script body. `[CmdletBinding()]` unlocks the common
parameters (`-Verbose`, `-ErrorAction`, and `-WhatIf`/`-Confirm` once `SupportsShouldProcess`
is declared) and exposes `$PSCmdlet`; `[Parameter(Mandatory, Position = n, ValueFromPipeline,
ValueFromPipelineByPropertyName)]` makes functions pipeline-native so bulk operations compose
without wrapper loops; `Validate*` attributes fail fast at the boundary before state changes
(the `SAFE-` posture in one line of metadata); comment-based help documents intent. Golden
template — copy this shape verbatim:

```powershell
function Set-ContosoServiceStartup {
    <#
    .SYNOPSIS Sets the startup type of a Contoso-managed Windows service.
    #>
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Medium')]
    param(
        [Parameter(Mandatory, Position = 0, ValueFromPipeline, ValueFromPipelineByPropertyName)]
        [ValidatePattern('^[A-Za-z][A-Za-z0-9_.-]{0,63}$')]      # boundary validation (ERR-014)
        [string]$Name,
        [Parameter(Mandatory, Position = 1)]
        [ValidateSet('Automatic', 'Manual', 'Disabled')]
        [string]$StartupType
    )
    process {
        try   { $service = Get-Service -Name $Name -ErrorAction Stop }   # ERR-001: terminating
        catch {
            Write-Error -Message "Service '$Name' not found on '$env:COMPUTERNAME'." `
                -Category ObjectNotFound -TargetObject $Name -ErrorId 'ServiceNotFound'
            return                                                       # next pipeline item
        }
        if ($PSCmdlet.ShouldProcess("service '$($service.Name)'", "set StartupType '$StartupType'")) {
            Set-Service -InputObject $service -StartupType $StartupType
            Add-Content "$env:ProgramData\Contoso\audit.log" `          # SEC-023: attribution
                ('{0};{1};{2};startup={3}' -f (Get-Date -Format o), $env:USERNAME,
                        $service.Name, $StartupType)
        }
    }
}
```
## 2. ShouldProcess done right

Destructive work must be previewable and confirmable. Declaring `SupportsShouldProcess` adds
`-WhatIf`/`-Confirm` to the public surface, and `$PSCmdlet.ShouldProcess(target, action)`
gates the mutation itself. WITHOUT — fires immediately, no preview, no prompt:

```powershell
function Remove-StaleProfile {
    param([string]$User)
    Remove-Item "C:\Users\$User" -Recurse -Force   # deletes on the first pipeline accident
}
```

WITH — dry-run, impact-scaled confirmation, precondition check:

```powershell
function Remove-StaleProfile {
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
    param(
        [Parameter(Mandatory, ValueFromPipelineByPropertyName)]
        [ValidatePattern('^[A-Za-z][A-Za-z0-9._-]{0,63}$')]   # rejects '..' traversal
        [string]$User
    )
    process {
        $dir = Join-Path -Path $env:SystemDrive -ChildPath "Users\$User"
        if (-not (Test-Path -LiteralPath $dir)) {
            Write-Error "Profile '$dir' missing." -Category ObjectNotFound -TargetObject $User; return
        }
        if ($PSCmdlet.ShouldProcess($dir, 'Remove profile directory')) {
            Remove-Item -LiteralPath $dir -Recurse -Force
        }
    }
}
```

What makes this correct rather than decorative: `ConfirmImpact = 'High'` prompts by default
because `$ConfirmPreference` starts at `Medium`, so approved automation passes
`-Confirm:$false` deliberately and visibly; `-WhatIf` output feeds `IDEM-` dry-run planning;
`ShouldContinue()` handles interactive second questions but honors neither `-Confirm` nor
`-WhatIf`, so pair it with a `-Force` switch; preference propagates to child cmdlets but not
to native executables, which you guard yourself.
## 3. Error-handling architecture

Three facts drive the design: `try/catch` sees only *terminating* errors, so fallible cmdlets
inside `try` need explicit `-ErrorAction Stop` (or a function-local `$ErrorActionPreference =
'Stop'`); library functions report per-item failures while controller scripts own global
policy; every failure leaves context a responder needs.

| Signal | Semantics | Emit when |
|---|---|---|
| `Write-Error` | Non-terminating; record reaches the error stream and `$Error`; caller continues | Per-item pipeline failures; caller owns retry/skip policy (`ERR-009`) |
| `throw` | Terminating; unwinds to the nearest caller `catch` | Preconditions violated such that continuing is meaningless |

Enrich records before re-emitting them — a bare `throw $_` discards identity:

```powershell
foreach ($node in $nodes) {
    try {
        Invoke-Command -ComputerName $node -ScriptBlock { hostname } -ErrorAction Stop
    }
    catch [System.Management.Automation.Remoting.PSRemotingTransportException] {
        $rec = [System.Management.Automation.ErrorRecord]::new($_.Exception, 'NodeUnreachable',
                 [System.Management.Automation.ErrorCategory]::OpenError, $node)
        Write-Error -ErrorRecord $rec
        continue   # next node; logged, not fatal (ERR-003)
    }
}
```

Avoid `trap`: scope-level behavior, confusing ordering against `finally`/`continue`, and it
hides failure policy away from the code raising it; `try/catch/finally` is localized,
greppable, and reserves `finally` for resource release only.
## 4. Logging: transcripts and a structured helper

Treat `Start-Transcript` as belt-and-suspenders, not a logging strategy: transcripts capture
host-visible output including anything echoed by accident, so leaked secrets persist in
plaintext (SEC-016); concurrent transcripts on one path collide; inside remoting the
transcript lands on the *target* machine; the format is prose, not queryable data. Primary
logging should be structured JSONL with an EventLog mirror for Event Viewer users:

```powershell
function Write-PrfLog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory, Position = 0)][string]$Message,
        [ValidateSet('Debug', 'Info', 'Warning', 'Error')][string]$Level = 'Info',
        [string]$Source = 'PRF'
    )
    $entry = [pscustomobject]@{
        Time = (Get-Date).ToString('o'); Level = $Level; Source = $Source
        User = $env:USERNAME; Computer = $env:COMPUTERNAME; Message = $Message
    } | ConvertTo-Json -Compress
    $logDir = Join-Path $env:ProgramData 'PRF\logs'
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null   # no-op when present
    Add-Content -Path (Join-Path $logDir 'prf.jsonl') -Value $entry -Encoding UTF8
    # COMP-016: Write-EventLog exists only in Windows PowerShell; PS 7 uses the .NET API
    if (Get-Command Write-EventLog -ErrorAction SilentlyContinue) {
        $type = @{ Error = 'Error'; Warning = 'Warning' }[$Level]; if (-not $type) { $type = 'Information' }
        Write-EventLog -LogName Application -Source $Source -EventId 1000 `
            -EntryType $type -Message $entry -ErrorAction SilentlyContinue
    }
}
```

The event source itself is created out-of-band by the installer (`New-EventLog`, elevation
required); generated scripts degrade gracefully to file-only logging and never log secrets.
## 5. Remoting patterns

Pass arguments through `param()` plus `-ArgumentList`: values bind on the remote side,
avoiding injection-shaped interpolation and accidental local expansion alike.

```powershell
$sb = {
    param([string]$SvcName, [string]$Mode)
    Set-Service -Name $SvcName -StartupType $Mode -PassThru
}
Invoke-Command -ComputerName SRV01.contoso.com -ScriptBlock $sb -ArgumentList 'W32Time', 'Automatic'
```

Etiquette: inside inline literals reach back explicitly with `$using:` — an unqualified
variable resolves remotely and returns empty, a classic silent failure. `-ComputerName`
accepts lists and throttles internally (~32 concurrent), so never hand-roll parallel machine
loops. Persistent sessions (`New-PSSession`) amortize connection cost across many calls but
must be removed in `finally`: leaked sessions exhaust WSMan capacity on busy hosts (ERR-011).
CredSSP is a last resort only — it delegates credentials wholesale to the intermediate host
for the double hop; prefer resource-based constrained delegation, or stage the payload
locally and run it under a scheduled task as SYSTEM (SEC-007 governs that registration).
## 6. Register-ScheduledTask: idempotent registration

Same inputs must produce the same task state on every run (`IDEM-009`); drift is reconciled,
never duplicated:

```powershell
$scriptPath = 'C:\Program Files\Contoso\Maintenance.ps1'     # signed artifact (SEC-007)
$exe        = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
# KC-01: pin the executable explicitly — pwsh.exe does not exist on 5.1-only hosts
$action     = New-ScheduledTaskAction -Execute $exe `
                -Argument ('-NoProfile -NonInteractive -File "{0}"' -f $scriptPath)
$trigger    = New-ScheduledTaskTrigger -Daily -At '02:30'
$settings   = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
$principal  = New-ScheduledTaskPrincipal -UserId 'NT AUTHORITY\SYSTEM' -RunLevel Highest
$name = 'Contoso Maintenance'; $path = '\Contoso\'           # trailing backslash required
if (Get-ScheduledTask -TaskName $name -TaskPath $path -ErrorAction SilentlyContinue) {
    Set-ScheduledTask -TaskName $name -TaskPath $path -Action $action -Trigger $trigger -Settings $settings
}
else {
    Register-ScheduledTask -TaskName $name -TaskPath $path -Action $action -Trigger $trigger `
        -Settings $settings -Principal $principal
}
```

This is a persistence change, so SEC-007 applies end-to-end: signed target, managed path,
named owner, recorded approval. `Get-ScheduledTask` emits a non-terminating error when absent,
silenced deliberately above instead of wrapping everything in `try`.
## 7. Service lifecycle etiquette

Distinguish *status* from *startup type* (starting is not enabling), query before mutating,
and always wait bounded:

```powershell
$svc = Get-Service -Name 'wuauserv' -ErrorAction Stop
if ($svc.StartType -eq 'Disabled') {
    Set-Service -Name $svc.Name -StartupType Manual      # enable before start attempts
}
if ($svc.Status -ne 'Running') { Start-Service -Name $svc.Name }
$svc.WaitForStatus('Running', (New-TimeSpan -Minutes 2)) # bounded, never open-ended sleep
```

`Restart-Service -Force` stops dependents too — enumerate dependents first and say so in
output; on timeout, fail loudly with an enriched record (`ERR-003`).
## 8. SecretManagement consumption pattern

Vault setup happens once per host from a documented runbook; consumption is the only
credential pattern PRF emits (SEC-014):

```powershell
Install-Module Microsoft.PowerShell.SecretManagement, Microsoft.PowerShell.SecretStore -Scope CurrentUser
Register-SecretVault -Name LocalStore -ModuleName Microsoft.PowerShell.SecretStore -DefaultVault
$cred = Get-Secret -Name 'Contoso/SqlAgent'              # stored as PSCredential
Invoke-Command -ComputerName SQL01 -Credential $cred -ScriptBlock { hostname }
```

Notes: `-AsPlainText` stays confined to fixtures (SEC-014); locked vaults unlock via
`Unlock-SecretVault` interactively, unattended hosts use their documented machine-scoped flow,
and vault contents remain barred from logs and transcripts (SEC-016).
## 9. Bulk AD / Azure etiquette

Filter server-side; client-side `Where-Object` drags the whole directory across the wire
before discarding most of it:

```powershell
$stale = Get-ADUser -Filter "Department -eq 'Sales'" -Properties LastLogonDate `
           -ResultPageSize 1000 -ResultSetSize 5000       # right: filtered on the DC
# Wrong: Get-ADUser -Filter * | Where-Object Department -eq 'Sales'
$stale | Select-Object SamAccountName, Enabled |
    Export-Csv .\pre-change-inventory.csv -NoTypeInformation   # rollback artifact (KS-21)
$stale | Disable-ADAccount -WhatIf                         # prove scope first (SAFE-013)
foreach ($u in $stale) {
    Disable-ADAccount -Identity $u -Confirm:$false         # deliberate, approved run
    Start-Sleep -Milliseconds 150                          # stay far below DC throttling
}
```

For Graph/Azure workloads: page via the SDK's paging support, honor `Retry-After` on HTTP 429
with exponential backoff and jitter, and batch writes where supported. Always exclude
break-glass accounts from bulk disable and stale-cleanup sweeps — they are the recovery path,
and locking them turns a bad day into an outage (SAFE-013; approvals per KS-21).
## 10. CI hooks preview — the v0.2/v0.3 bridge

Both enforcement tools work today; formalizing them as PRF rule series lands in v0.2 (lint)
and v0.3 (tests):

```yaml
- run: Install-Module PSScriptAnalyzer, Pester -Scope CurrentUser -Force
- run: Invoke-ScriptAnalyzer -Path ./src -Recurse -Severity Warning -EnableExit
- run: $cfg = New-PesterConfiguration; $cfg.Run.Exit = $true; Invoke-Pester -Configuration $cfg
```

Map analyzer severities onto the `SAFE-`/`COMP-` series so lint findings become rule findings,
and write Pester tests that assert idempotency directly: call twice, assert the second run
changes nothing observable (every `IDEM-` rule). Until those series ship, treat this as the manual bar.

Cross-references: destructive-operation gating lives in `SEC-*`; failure contracts and record
enrichment in `ERR-`; execution safety (sessions, waits, break-glass) in `SAFE-`;
same-input-same-state guarantees in `IDEM-`; 5.1-vs-7.x deltas above in `COMP-`.
