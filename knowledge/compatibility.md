# Compatibility Matrix: Windows PowerShell 5.1 vs PowerShell 7.x (COMP Rules)

Windows ships **two** PowerShells, and they disagree about syntax, defaults, cmdlets, and modules. Every rule in this framework carrying the `COMP-` prefix exists because an agent assumed one engine while the target host ran the other. Read the engine identity off `$PSVersionTable` before emitting a single command (KC-01), then consult this chapter. Seed index used throughout (seed numbers are local to this chapter, not rule IDs; the table below maps each seed to the canonical `COMP-` rules in `rules/reliability-rules.yaml`): KC-01 know your engine; KC-02 guard the `$Is*` automatic variables; KC-03 zero WMI cmdlets in dual-runtime code; KC-04 pin encodings explicitly; KC-05 verify modules and their external dependencies per host; KC-06 parse-gate against the oldest supported engine; KC-07 treat experimental features as absent; KC-08 choose the remoting transport deliberately; KC-09 expect parameter-name drift between engines; KC-10 prefer the modern equivalent because it usually exists in 5.1 too.

| Seed | Canonical rules |
|---|---|
| KC-01 | COMP-017 |
| KC-02 | COMP-011, COMP-021 |
| KC-03 | COMP-014, COMP-015, COMP-016 |
| KC-04 | COMP-009 |
| KC-05 | COMP-019, COMP-020 |
| KC-06 | COMP-001, COMP-002, COMP-003, COMP-004, COMP-005, COMP-017 |
| KC-07 | COMP-024 |
| KC-08 | COMP-013, COMP-018 |
| KC-09 | COMP-012 |
| KC-10 | COMP-010, COMP-014, COMP-016 |

## 1. Choosing the Target Runtime

| Dimension | Windows PowerShell 5.1 | PowerShell 7.x |
|---|---|---|
| Executable | `powershell.exe` | `pwsh.exe` |
| `$PSVersionTable.PSEdition` | `Desktop` | `Core` |
| Runtime base | .NET Framework 4.x, Windows-only | .NET (LTS-aligned; 7.4 rides .NET 8), cross-platform |
| Distribution | Inbox in Windows 10/11 and Server 2016+; cannot be uninstalled or upgraded in place | Separate MSI/package/Store install; sits side by side, never modifies 5.1 |
| Release model | Frozen forever; fixes arrive only through Windows servicing | Roughly annual minors; even-numbered minors are LTS (7.2, 7.4) |
| Language surface | Frozen at 5.1 syntax | Adds `&&`, ternary, `??`, null-conditional members, `-Parallel`, `.Clean()`, more |
| Remoting transports | WinRM only | WinRM plus SSH-based remoting (KC-08) |

**Target 5.1 only when:** the environment forbids third-party software; a vendor contract or GAC'd .NET Framework assembly demands the Desktop edition; or you are maintaining existing 5.1 automation with no upgrade window. **Target 7.x for:** anything newly written, especially agent-driven tooling; cross-platform fleets; current gallery modules (Az.*, Microsoft.Graph.*, Pester 5); and performance-sensitive work (startup time, JSON handling, parallel loops). Windows administration is fully in scope for 7.x on Windows 10/11 and Server once the relevant RSAT modules are present. Never write "PowerShell" without knowing which engine executes it — probe first, then commit to a syntax level (KC-01).

## 2. Feature Delta: 5.1 Versus 7.x

| Capability | Windows PowerShell 5.1 | PowerShell 7.x | Rule |
|---|---|---|---|
| Pipeline chain operators | Not parsed; `&&` is a syntax error | `a && b` runs on success, failure-chaining via the doubled-bar operator | KC-06 |
| Ternary conditional | Absent | `$cond ? $a : $b` | KC-06 |
| Null-coalescing | Absent | `$x ?? 'fallback'` and assign-if-null `$x ??= 'init'` | KC-06 |
| Null-conditional member/index | Absent | `$obj?.Prop`, `$arr?[0]`, `$obj?.Method()` | KC-06 |
| Parallel pipeline | Absent | `ForEach-Object -Parallel` with `-ThrottleLimit` (default 5) | KC-06 |
| ThreadJob alternative | `Start-ThreadJob` installable from the Gallery | Built-in ecosystem; ThreadJob still works | — |
| `Test-Connection` shape | `-ComputerName`, emits `Win32_PingStatus` (`.ResponseTime`, `.StatusCode`); credential knobs because it rides WMI | `-TargetName`, emits `PingStatus` (`.Latency`, `.Status`); raw ICMP adds `-Continuous`, `-MtuSize`, `-Repeat` (7.2+) | KC-09 |
| Deep error inspection | `$Error[0]` plus `Format-List * -Force` spelunking | `Get-Error [-Newest N]`; `ConciseView` is the default `$ErrorView` | KC-01 |
| String joining | Hand-rolled projection then `-join` | `Join-String` with `-Property`, `-Separator`, `-Format` | — |
| JSON typing | `ConvertFrom-Json` always yields `PSCustomObject`; duplicate or case-clashing keys throw | `-AsHashtable` yields a hashtable, tolerates keys that are illegal property names, parses faster | — |
| File-write defaults | `Out-File` and `>` emit UTF-16LE ("Unicode"); `Set-Content` emits the ANSI codepage; `Export-Csv` emits ASCII | `utf8NoBOM` across the file-writing cmdlets | KC-04 |
| Control-character cleanup | Regex: `-replace '\p{Cc}', ''` | `.Clean()` string method (7.4+) | — |
| OS automatic variables | `$IsWindows`, `$IsLinux`, `$IsMacOS` DO NOT EXIST (evaluate to null; strict mode raises an error) | Real booleans reflecting the host OS | KC-02 |
| SSH remoting | WinRM only | `New-PSSession -HostName`, `-SSHTransport`, key-based auth, any OS pairing | KC-08 |
| Experimental features | Unsupported | `Get-ExperimentalFeature` / `Enable-ExperimentalFeature`; catalog changes per minor version | KC-07 |

### 2.1 Minimal Probes

```powershell
Test-Path $lockFile && Remove-Item $lockFile          # second pipeline runs only on success
New-Item -ItemType Directory $dest || throw "cannot create $dest"
$level = $detail ? 'Debug' : 'Info'                   # ternary (7.0+)
$owner = $env:DEPLOY_OWNER ?? 'unassigned'            # null-coalescing
$stamp = $job?.FinishTime?.ToString('u')              # null-conditional member chain
```

```powershell
# Bounded fan-out (7.0+; each input lands in its own runspace)
$servers | ForEach-Object -Parallel {
    Test-Connection -TargetName $_ -Count 1 -Quiet
} -ThrottleLimit 8
```

Inside `-Parallel`, `$_` flows automatically but outer variables need `$using:` and caller-defined functions are invisible; completion order is not guaranteed. The honest 5.1 fallback is the Gallery `ThreadJob` module (`Start-ThreadJob`) or a plain `foreach` — pick one code path deliberately rather than shipping syntax 5.1 cannot parse (KC-06).

```powershell
Test-Connection -ComputerName SRV01 -Count 2   # 5.1: Win32_PingStatus; .ResponseTime / .StatusCode
Test-Connection -TargetName    SRV01 -Count 2  # 7.x: PingStatus;      .Latency     / .Status
```

```powershell
'piñata' | Out-File u.txt     # 5.1: UTF-16LE        7.x: utf8NoBOM
'piñata' > r.txt              # 5.1: UTF-16LE        7.x: utf8NoBOM
'piñata' | Set-Content s.txt  # 5.1: ANSI codepage   7.x: utf8NoBOM
```

```powershell
Get-Error -Newest 3                                    # 7.x deep dive into the error chain
$Error[0] | Format-List * -Force                       # closest 5.1 equivalent
Get-ChildItem *.log | Join-String -Property Name -Separator '; '
$cfg = Get-Content app.json -Raw | ConvertFrom-Json -AsHashtable   # 7.x hashtable mode
```

```powershell
$pasted = "INV-0042`0`bX"          # stray NUL and backspace scraped from a log
$pasted.Clean()                    # 7.4+ only: control characters stripped
$pasted -replace '\p{Cc}', ''      # identical outcome on 5.1 and every 7.x (KC-10)
```

```powershell
if ($PSVersionTable.PSEdition -eq 'Core' -and $IsWindows) { 'PowerShell 7 on Windows' }
elseif ($env:OS -eq 'Windows_NT') { 'Windows PowerShell 5.1' }
else { 'PowerShell 7 on Linux/macOS' }
```

The OS probe works because `-and` short-circuits: on 5.1 the first clause is false, so `$IsWindows` is never evaluated — even under `Set-StrictMode` (KC-02). Referencing `$IsWindows` bare on 5.1 yields null, so `if (-not $IsWindows)` wrongly takes the non-Windows branch on a Windows box; that single mistake justifies the whole KC-02 rule.

## 3. Cmdlet Migrations

PowerShell 7 deleted the entire WMI cmdlet family: `Get-WmiObject`, `Set-WmiInstance`, `Invoke-WmiMethod`, `Remove-WmiObject`, and `Register-WmiEvent` throw `CommandNotFound`, and the `[wmi]` / `[wmiclass]` accelerators are gone with them. The CIM replacements have existed since Windows PowerShell 3.0, so writing CIM-first costs nothing on 5.1 and survives 7.x untouched (KC-03, KC-10). Expect behavioral deltas: `Get-CimInstance` returns deserialized snapshot instances whose methods are not directly invocable, WMI's `__SERVER` property becomes `PSComputerName`, `-Filter` still accepts the same WQL, and ancient DCOM-only endpoints need `New-CimSession -SessionOption (New-CimSessionOption -Protocol DCOM)`.

| Removed or deprecated | Write instead | Notes |
|---|---|---|
| `Get-WmiObject` | `Get-CimInstance` | Works in 5.1 AND 7.x; WMI form deleted in 7 (KC-03) |
| `Set-WmiInstance` | `Set-CimInstance` | Same story |
| `Invoke-WmiMethod` | `Invoke-CimMethod` | Methods are no longer attached to the objects themselves |
| `Remove-WmiObject` | `Remove-CimInstance` | |
| `Register-WmiEvent` | `Register-CimIndicationEvent` | |
| `[wmiclass]'X'` / `[wmi]`path casts | `Get-CimClass` / `Get-CimInstance` | Accelerators removed in 7 |
| `Get-EventLog` | `Get-WinEvent -FilterHashtable` | Deprecated since 3.0, absent in 7.x |
| `Write-EventLog` | .NET `System.Diagnostics.EventLog` API | No direct cmdlet port; source registration still applies |

```powershell
$os = Get-CimInstance -ClassName Win32_OperatingSystem            # valid in 5.1 and 7.x
$spooler = Get-CimInstance Win32_Service -Filter "Name='Spooler'"
Invoke-CimMethod -InputObject $spooler -MethodName StopService    # explicit invocation required
```

`Get-WinEvent` exists in both engines, which makes it the canonical KC-10 showcase. Two traps for agents: it emits a non-terminating error when zero events match (silence it or you will report false failures), and results arrive newest-first unless you pass `-Oldest` for chronological processing.

```powershell
Get-WinEvent -FilterHashtable @{
    LogName   = 'System'
    Level     = 1, 2                       # Critical and Error
    StartTime = (Get-Date).AddDays(-1)
} -MaxEvents 100 -ErrorAction SilentlyContinue
```

## 4. Module Availability Reality

A module name resolving is not the same as a capability existing. Classify every dependency before promising it (KC-05):

| Tier | Examples | Provenance | Guidance |
|---|---|---|---|
| Inbox, both engines | Microsoft.PowerShell.Management, Utility, Security | Shipped in each engine's `$PSHOME` (`System32\...\v1.0` vs `Program Files\PowerShell\7`) | Safe everywhere; behavior can still differ subtly (encodings, culture) |
| Inbox, Windows-bound | ScheduledTasks, NetAdapter, Defender | OS components with .NET Framework-era assemblies | Many load in 7 on Win10+; verify per module; `Import-Module -UseWindowsPowerShell` (7-only, Windows-only) proxies stubborn 5.1 modules |
| RSAT-dependent | ActiveDirectory, GroupPolicy, DnsServer, DhcpServer | Optional Features / Windows capabilities — neither the OS base nor either engine ships them | Installing the engine proves nothing; see below |
| Gallery, cross-platform | Az.*, Microsoft.Graph.*, Pester 5.x, PSScriptAnalyzer, ThreadJob | PowerShell Gallery via `Install-Module` | Installed per engine (5.1 and 7 keep separate module paths); pin versions in automation |
| Effectively 5.1-only | Modules bound to GAC / .NET-Framework-only assemblies or legacy COM | Varies | Isolate them; do not promise Core ports without testing |

RSAT installation for the ActiveDirectory module:

```powershell
# Client Windows 10/11 — optional capability
Add-WindowsCapability -Online -Name Rsat.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0
# Windows Server
Install-WindowsFeature RSAT-AD-PowerShell
```

After installation, `Get-Module -ListAvailable ActiveDirectory` succeeding proves nothing about usability: the first `Get-ADUser` performs Kerberos authentication and LDAP (389/636) against a discoverable domain controller. An offline administrative workstation imports the module happily and then fails on every call — module present, dependency absent. KC-05 therefore requires probing both layers, module AND dependency, on the target host before claiming the capability. Gallery notes: 5.1 ships a fossilized inbox Pester 3.4 that must never be updated in place — install Pester 5.x to the user scope and import it explicitly or the inbox copy shadows it; Az.* runs on both editions but rewards 7.x startup and memory behavior; the Microsoft.Graph.* SDK nominally targets both editions on Windows, yet its authentication and dependency stack behaves most reliably on 7.x.

## 5. Execution Policy Applicability

| Context | Enforced? | Defaults and storage |
|---|---|---|
| Windows PowerShell on Windows | Yes | Default `Restricted` on client SKUs, `RemoteSigned` on Server; registry under `...\PowerShell\1\ShellIds\Microsoft.PowerShell` |
| PowerShell 7 on Windows | Yes, in its own store | Unset defaults to `RemoteSigned`; registry under `PowerShellCore\ShellIds\Microsoft.PowerShell`; GPO scopes override |
| Any engine on Linux/macOS | No | `Get-ExecutionPolicy` returns `Undefined`; `Set-ExecutionPolicy` throws `PlatformNotSupportedException`; scripts run regardless |

Group Policy scopes (`MachinePolicy`, `UserPolicy`) bind both engines on Windows and cannot be overridden locally; `Process`, `CurrentUser`, and `LocalMachine` are per-engine settings, which is why "I already ran Set-ExecutionPolicy" fixes one console and not the other. Automation must never repair policy by weakening it — not at machine scope, not for the session, and not with `-ExecutionPolicy Bypass` on the command line (SEC-010, SAFE-009): sign the script or clear a verified Mark-of-the-Web with `Unblock-File`, and treat policy state as part of the environment probe (KC-05). Remember that under `RemoteSigned`, files carrying the Mark-of-the-Web Zone.Identifier must be signed on both engines — extraction tools that strip zones silently change what runs.

## 6. Writing Dual-Runtime Scripts

Declare the floor with `#Requires` so unsupported hosts fail loudly instead of mysteriously (KC-06):

```powershell
#Requires -Version 5.1               # floor for dual-runtime scripts
#Requires -PSEdition Core            # optional extra gate; values: Desktop, Core
# To demand 7.x exclusively:         #Requires -Version 7.0
```

`#Requires` cannot rescue you from syntax: the 5.1 parser rejects `&&`, ternaries, `?.`, and `??` ANYWHERE in the file, including inside version-guarded branches that would never execute. Syntax-level divergence therefore demands file splitting, not conditional execution (KC-06):

```powershell
# runner.ps1 — parses cleanly under BOTH engines
if ($PSVersionTable.PSVersion.Major -ge 6) {
    . (Join-Path $PSScriptRoot 'modern-core.ps1')     # free to use chain operators, -Parallel
}
else {
    . (Join-Path $PSScriptRoot 'legacy-desktop.ps1')  # 5.1-safe implementations
}
```

Within the shared, parse-safe layer, reach for these replacements first:

| Instead of (5.1-era) | Write | Why |
|---|---|---|
| `Get-WmiObject` / `Invoke-WmiMethod` / `Set-WmiInstance` / `Remove-WmiObject` | The matching `*-Cim*` cmdlets | Exist in 5.1 AND 7.x; WMI forms deleted in 7 (KC-03) |
| `Register-WmiEvent` | `Register-CimIndicationEvent` | Same rationale |
| `[wmiclass]` / `[wmi]` casts | `Get-CimClass` / `Get-CimInstance` | Accelerators removed in 7 (KC-03) |
| `Get-EventLog` / `Write-EventLog` | `Get-WinEvent` / .NET EventLog API | Removed in 7.x (KC-03) |
| Bare `Out-File`, `>`, `Set-Content`, `Export-Csv` | Explicit `-Encoding UTF8` or `ASCII` | Engine defaults diverge (KC-04); note `utf8NoBOM` itself is a 7-only argument |
| `Test-Connection -ComputerName` | Version branch, or `System.Net.NetworkInformation.Ping` | Identical semantics on both engines (KC-09) |
| `ForEach-Object -Parallel` | `Start-ThreadJob` (installs on 5.1) or plain `foreach` | One code path, both engines (KC-06) |
| Bare `$IsWindows` reads | `$env:OS -eq 'Windows_NT'` or PSEdition-gated access | Variable undefined on 5.1 (KC-02) |
| `Get-Error` | `$Error[0]` plus `Format-List * -Force` | Closest 5.1 view of the error record |

## 7. Pre-Flight Probe Checklist

Run every probe on the TARGET host, not the authoring host, and attach the output to the task record — a compatibility claim without probe evidence is an assumption (KC-01):

| Probe | Pass criterion | Rule |
|---|---|---|
| Record engine identity via `$PSVersionTable` (version + edition) | Chosen syntax and parameters match the observed engine | KC-01 |
| Parse the script under `powershell.exe` with `[scriptblock]::Create(...)` | No `ParseException`; catches leaked `&&`, ternary, `??` syntax | KC-06 |
| Scan for dead cmdlets: `*-Wmi*`, `[wmiclass]`, `[wmi]`, `Get-EventLog` | Zero hits | KC-03 |
| Audit every file-writing cmdlet for an explicit `-Encoding` argument | No reliance on engine defaults | KC-04 |
| Inspect each `$IsWindows` / `$IsLinux` / `$IsMacOS` reference for a guard | None reachable unguarded by 5.1 | KC-02 |
| Probe module presence AND dependency (RSAT installed, DC line-of-sight, policy state) | Both layers verified | KC-05 |
| Search shipped scripts for `Enable-ExperimentalFeature` reliance | None; experimental features treated as absent | KC-07 |
| Name the remoting transport per hop: WinRM (`-ComputerName`) or SSH (`-HostName`) | Matches fleet reality | KC-08 |
| Spot-check drifted parameters (e.g. `Test-Connection`) against the target engine's help | Names valid per engine | KC-09 |
| Review WMI/event-log code for CIM / `Get-WinEvent` modernization | Future-proofed even where 5.1 suffices today | KC-10 |

```powershell
# Scanner one-liners for the checklist above (run in any engine)
Select-String -Path *.ps1 -Pattern 'Get-WmiObject|Invoke-WmiMethod|Set-WmiInstance|Register-WmiEvent|Remove-WmiObject'
Select-String -Path *.ps1 -Pattern '\[wmiclass\]|\[wmi\]|Get-EventLog|Write-EventLog'
Select-String -Path *.ps1 -Pattern '\$Is(Windows|Linux|MacOS)'    # inspect each hit for a guard
Select-String -Path *.ps1 -Pattern '(Out-File|Set-Content|Add-Content|Export-Csv)(?!.*-Encoding)'
Select-String -Path *.ps1 -Pattern '&&|\?\?|\?\.|Get-ExperimentalFeature'  # syntax leaks needing KC-06 triage
```

Five minutes of probing buys a script that runs identically on the inbox engine in a locked-down enterprise and on the current LTS in a container — which is precisely the standard the COMP rules exist to enforce.
