# PRF Anti-Pattern Catalog — Part 1 (AP-01 … AP-12)
During Generation Protocol Step 4 self-review, compare every generated PowerShell artifact against each entry below; a match is a defect, not a style preference — apply the listed **Repair**, record the AP id in the self-review log, and cite the matching Related rule categories in the delivery report.
A clean pass proves little by itself: these entries document known failure modes only, so Part 2 (AP-13 onward) and the `rules/` category checks remain mandatory.
Unless an entry states otherwise, every snippet is written for Windows PowerShell 5.1 and PowerShell 7.x alike.
### AP-01 — Aliases in production scripts
**Symptom**: Interactive shortcut aliases (`gci`, `%`, `?`, `cat`, `mkdir`) shipped in unattended scripts.
**Bad**:
```powershell
gci C:\Logs -Recurse | ? Extension -eq '.log' | % { cat $_.FullName }
```
**Why it fails**: Aliases are console conveniences, not API: hosts, profiles, or policy can leave them undefined, grep-based review cannot find them, and `mkdir` masks `New-Item -ItemType Directory` semantics.
**Risk**: medium — **Related**: COMP-, SAFE-
**Repair**:
```powershell
Get-ChildItem C:\Logs -Recurse | Where-Object Extension -eq '.log' | ForEach-Object { Get-Content $_.FullName }
```
### AP-02 — Write-Host used as a data channel
**Symptom**: Data meant for downstream tooling is emitted with `Write-Host`, so consumers capture an empty pipeline.
**Bad**:
```powershell
Write-Host (ConvertTo-Csv $inventory)   # caller does $out = .\Export-Inventory.ps1 and gets $null
```
**Why it fails**: `Write-Host` writes to the information stream/console, never the success pipeline, so ordinary redirects and `$out = .\script.ps1` capture nothing; emit objects or strings and reserve `Write-Host` for interactive status.
**Risk**: medium — **Related**: COMP-, IDEM-
**Repair**:
```powershell
$inventory | ConvertTo-Csv   # success pipeline; Write-Verbose / Write-Information for diagnostics
```
### AP-03 — Reliance on positional parameters
**Symptom**: Calls depend on argument order rather than named parameters.
**Bad**:
```powershell
Publish-Pkg web 2.1.0 C:\out\pkg.zip   # binds Position 0/1/2 blindly
```
**Why it fails**: Positional binding silently re-binds when a parameter is inserted or reordered, and reviewers cannot tell which value feeds which parameter; declare `[Parameter()]` attributes and pass names at call sites.
**Risk**: medium — **Related**: COMP-, IDEM-
**Repair**:
```powershell
Publish-Pkg -Name web -Version 2.1.0 -Path C:\out\pkg.zip   # parameters declared with [Parameter(Mandatory)]
```
### AP-04 — Backtick line continuation
**Symptom**: Committed lines end with a backtick escape instead of breaking at a pipeline element.
**Bad**:
```powershell
$running = Get-Service `
    -DisplayName 'Windows*' | Select Name,Status
```
**Why it fails**: A single invisible space after a backtick breaks parsing or changes meaning, and the character is lost or corrupted in diffs, mail, and JSON transport; end lines after a pipe (or splat a hashtable) instead.
**Risk**: low — **Related**: COMP-, IDEM-
**Repair**:
```powershell
$running = Get-Service -DisplayName 'Windows*' | Select-Object Name, Status   # break AFTER pipes
```
### AP-05 — Post-mortem `$Error[0]` inspection instead of handling errors where they occur
**Symptom**: Failures are peeked at via `$Error[0]` after the fact instead of being handled at the failing statement.
**Bad**:
```powershell
Copy-Item C:\cfg\web.config \\srv01\cfg\; if ($Error.Count) { "WARN $($Error[0])" }
```
**Why it fails**: `$Error[0]` holds the newest error from anywhere in the session — not necessarily this statement — and execution already continued onto suspect state; handle failures locally with `-ErrorAction Stop` inside `try/catch`.
**Risk**: high — **Related**: ERR-, SAFE-
**Repair**:
```powershell
try { Copy-Item C:\cfg\web.config \\srv01\cfg\ -ErrorAction Stop } catch { throw "Config copy failed: $($_.Exception.Message)" }
```
### AP-06 — Empty `catch {}`
**Symptom**: `catch` blocks that neither log, fall back, nor rethrow.
**Bad**:
```powershell
try { $state = Import-Clixml C:\state\job.xml } catch {}
```
**Why it fails**: An empty handler swallows access-denied, corrupt input, and disk-full alike, then lets the script continue on missing or stale data with no trace for operators or debuggers.
**Risk**: high — **Related**: ERR-, SAFE-
**Repair**:
```powershell
try { $state = Import-Clixml C:\state\job.xml -ErrorAction Stop } catch { Write-Warning "No saved state ($_): using defaults"; $state = @{} }
```
### AP-07 — `catch { throw '<literal>' }` noise that discards context
**Symptom**: Handlers replace the caught error with a fresh literal message.
**Bad**:
```powershell
try { Start-Process msiexec.exe "/i $msi /qn" -Wait -ErrorAction Stop } catch { throw 'Install failed.' }
```
**Why it fails**: Throwing a string erases the original ErrorRecord — exception type, stack trace, `InvocationInfo`, inner exceptions — so root cause becomes untraceable; log extra context beside the record, then rethrow it untouched with bare `throw`.
**Risk**: medium — **Related**: ERR-, COMP-
**Repair**:
```powershell
try { Start-Process msiexec.exe "/i $msi /qn" -Wait -ErrorAction Stop } catch { Write-Warning "msiexec failed for '${msi}': $($_.Exception.Message)"; throw }
```
### AP-08 — Ignoring `$LASTEXITCODE` of native tools
**Symptom**: Native executables run unchecked; the script reports success regardless of their exit status.
**Bad**:
```powershell
git clone $url C:\build\app; robocopy C:\bin \\dep01\bin /MIR; 'Deployment complete'
```
**Why it fails**: Native commands never throw: a nonzero `$LASTEXITCODE` does not halt the pipeline, and robocopy signals success below 8, so half-cloned or half-mirrored trees pass unnoticed.
**Risk**: high — **Related**: ERR-, SAFE-, COMP-
**Repair**:
```powershell
git clone $url C:\build\app; if ($LASTEXITCODE) { throw "git clone failed ($LASTEXITCODE)" }
robocopy C:\bin \\dep01\bin /MIR; if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" }
```
### AP-09 — Invoke-Expression string templating
**Symptom**: Commands are assembled by interpolation and evaluated with `Invoke-Expression`.
**Bad**:
```powershell
Invoke-Expression "Remove-Item $userInput -Recurse -Force"   # $userInput comes from ticket JSON
```
**Why it fails**: Any metacharacter in the interpolated value (`;`, `$(...)`, quotes) becomes executed code — full command injection — and templated strings defeat static analysis; invoke commands directly, pass values as arguments, and use splatting for optional parts.
**Risk**: critical — **Related**: SEC-, ERR-
**Repair**:
```powershell
Remove-Item -LiteralPath $userInput -Recurse -Force   # values as arguments; & operator + splatting for dynamic calls
```
### AP-10 — String-concatenated paths instead of Join-Path
**Symptom**: Paths are glued with `+` or `"$a\$b"` interpolation instead of `Join-Path`.
**Bad**:
```powershell
$out = "$env:SystemDrive\Temp" + '\' + $env:USERNAME + '\dump.json'
```
**Why it fails**: Manual separators duplicate or drop `\`, break on UNC paths and registry-style roots, and scatter path logic across the script; `Join-Path` normalizes separators and composes cleanly.
**Risk**: medium — **Related**: COMP-, SAFE-
**Repair**:
```powershell
$out = Join-Path (Join-Path (Join-Path $env:SystemDrive 'Temp') $env:USERNAME) 'dump.json'
```
### AP-11 — Hardcoded passwords
**Symptom**: Plaintext passwords embedded in script bodies, config files, or command lines.
**Bad**:
```powershell
net.exe use \\file01\backup /user:CORP\svc_backup 'Summer2024!'
```
**Why it fails**: Literal credentials leak into git history, CI logs, transcripts, and crash dumps and survive every rotation; load them from SecretManagement/a vault or a DPAPI-protected credential, and grant the account least privilege.
**Risk**: critical — **Related**: SEC-, SAFE-
**Repair**:
```powershell
$cred = Get-Secret 'CORP/svc_backup'; New-PSDrive -Name Backup -PSProvider FileSystem -Root \\file01\backup -Credential $cred | Out-Null   # credential object, never argv
```
### AP-12 — ConvertTo-SecureString -AsPlainText -Force
**Symptom**: SecureStrings fabricated from plaintext literals to satisfy credential parameters.
**Bad**:
```powershell
$sa = New-Object PSCredential('sa', (ConvertTo-SecureString 'S3cret!' -AsPlainText -Force))
```
**Why it fails**: `-AsPlainText -Force` launders a literal into a SecureString while the plaintext persists in source, history, and transcripts — the result protects nothing; prompt with `Read-Host -AsSecureString`, use a vault, or persist once via `ConvertFrom-SecureString` (key/DPAPI).
**Risk**: critical — **Related**: SEC-, SAFE-, ERR-
**Repair**:
```powershell
$sec = Read-Host 'svc password' -AsSecureString; $sec | ConvertFrom-SecureString | Set-Content C:\secrets\svc.bin   # DPAPI-bound (Windows); or Get-Secret
```

## AP-13 — legacy `Get-WmiObject` usage
**Symptom**: Works on Windows PowerShell 5.1, dies on PowerShell 6/7 with `CommandNotFoundException`; the `gwmi` alias hides the dependency until the worst moment.
**Bad**:
```powershell
$os = Get-WmiObject Win32_OperatingSystem
```
**Why it fails**: The WMI cmdlets ship only with the WMF 5.1-era module set — PowerShell 7 has no `Get-WmiObject` — and they ride deprecated DCOM instead of WSMan/CIM.
**Risk**: medium | **Related**: COMP-, ERR-
**Repair**:
```powershell
$os = Get-CimInstance -ClassName Win32_OperatingSystem
```
## AP-14 — `Remove-Item -Recurse -Force` with wildcards
**Symptom**: A cleanup one-liner deletes vastly more than intended — up to the whole drive — when an interpolated variable is empty or carries wildcard metacharacters.
**Bad**:
```powershell
Remove-Item "$base\$sub\*.cache" -Recurse -Force
```
**Why it fails**: With `$base` empty the pattern becomes rooted `\*.cache` at the current drive; wildcards expand before deletion and `-Recurse` answers the container-deletion prompt for you, so nothing halts the sweep.
**Risk**: critical | **Related**: SAFE-, ERR-
**Repair**:
```powershell
$d = Join-Path (Resolve-Path $base -ErrorAction Stop) $sub; Get-ChildItem -LiteralPath $d -File | Remove-Item -Force
```
## AP-15 — `Start-Process` without `-Wait`/`-PassThru` when results matter
**Symptom**: The script declares victory the instant it spawns an installer or tool; later steps read output that does not exist yet, and the child's exit code vanishes.
**Bad**:
```powershell
Start-Process msiexec.exe -ArgumentList '/i', 'pkg.msi', '/qn'; Publish-Website
```
**Why it fails**: `Start-Process` is asynchronous and returns nothing by default: without `-Wait` every following statement races the child, and without `-PassThru` there is no process object carrying `ExitCode` to assert on.
**Risk**: high | **Related**: ERR-, IDEM-
**Repair**:
```powershell
$p = Start-Process msiexec.exe -ArgumentList '/i','pkg.msi','/qn' -Wait -PassThru
if ($p.ExitCode -ne 0) { throw "msiexec failed with exit code $($p.ExitCode)" }
```
## AP-16 — embedding variables into native command-line strings
**Symptom**: A helper builds one big command string; input containing quotes, spaces, or `;`/`&` stops being data and runs as extra commands with the script's privileges.
**Bad**:
```powershell
Invoke-Expression "net user '$userName' /active:no"
```
**Why it fails**: `Invoke-Expression` (like any quote-concatenated native command) re-parses the text as grammar, so `$userName = "x'; shutdown /r /t 0'"` executes — textbook command injection.
**Risk**: critical | **Related**: SEC-, ERR-
**Repair**:
```powershell
net.exe user $userName /active:no   # passed as separate argv, never re-parsed
```
## AP-17 — piping through `Format-Table` before `Export-Csv`
**Symptom**: The exported CSV holds one opaque column of formatting-record internals (an opaque `ClassId…` column in 5.1) or blank padded cells instead of the requested data columns.
**Bad**:
```powershell
Get-Process | Format-Table Name,WS | Export-Csv procs.csv -NoTypeInformation
```
**Why it fails**: `Format-*` cmdlets emit transient formatting directives, not your objects; `Export-Csv` dutifully serializes those throwaway records, so real data never reaches the file.
**Risk**: low | **Related**: ERR-, IDEM-
**Repair**:
```powershell
Get-Process | Select-Object Name,WS | Export-Csv procs.csv -NoTypeInformation
```
## AP-18 — `-eq`/`-ne` against collections and `$null` placement
**Symptom**: Guards behave inverted or inert: "is it null" checks pass on empty pipelines, and permission checks lock out users who demonstrably hold the required role.
**Bad**:
```powershell
if ($servers -eq $null) { Write-Warning 'no servers found' }
if ($roles -ne 'admin') { Deny-Access }
```
**Why it fails**: With a collection on the left, `-eq`/`-ne` become element FILTERS, not comparisons: line 1 asks "does any element equal `$null`?", line 2 fires whenever any role is not admin — neither tests what the author meant.
**Risk**: medium | **Related**: ERR-, SAFE-
**Repair**:
```powershell
if ($null -eq $servers) { Write-Warning 'no servers found' }; if (-not ($roles -contains 'admin')) { Deny-Access }
```
## AP-19 — unwrapped pipeline `.Count` on single results
**Symptom**: `"count: $($procs.Count)"` prints an empty number on 5.1 when nothing matched, throws under `Set-StrictMode`, and silently reports 1 for a lone object — the display flips with cardinality.
**Bad**:
```powershell
$procs = Get-Process chrome -ErrorAction SilentlyContinue; "n=$($procs.Count)"
```
**Why it fails**: Pipelines unwrap: zero hits yield `$null`, whose `.Count` quietly stays `$null` on 5.1 and is a `PropertyNotFoundException` in strict mode; a single object relies on intrinsic members some hosts never honor.
**Risk**: low | **Related**: ERR-, COMP-
**Repair**:
```powershell
$n = @($procs).Count   # array subexpression guarantees a real integer: 0, 1, or N
```
## AP-20 — `Test-Path` wildcard-vs-literal confusion
**Symptom**: Existence checks return False for files that plainly exist — almost always names containing square brackets such as `report[1].pdf` or `trace[2024].log`.
**Bad**:
```powershell
if (Test-Path $download) { Remove-Item $download }
```
**Why it fails**: `-Path` compiles the value into a wildcard pattern, so `[1]` is a character class matching nothing; the guard silently skips real files, and a stray `*` can match unrelated targets.
**Risk**: medium | **Related**: ERR-, IDEM-
**Repair**:
```powershell
if (Test-Path -LiteralPath $download) { Remove-Item -LiteralPath $download }
```
## AP-21 — unguarded `New-Item`
**Symptom**: "already exists" or provider errors drift past as non-terminating noise; downstream copies land nowhere or explode much later with confusing missing-path messages.
**Bad**:
```powershell
New-Item -Path $outDir -ItemType Directory; Copy-Item payload.zip $outDir
```
**Why it fails**: The default `$ErrorActionPreference` is Continue, so a failed creation still runs `Copy-Item`, which then helpfully creates a FILE named like the directory; existing paths error too, so neither outcome is deterministic.
**Risk**: medium | **Related**: ERR-, IDEM-
**Repair**:
```powershell
New-Item -Path $outDir -ItemType Directory -Force -ErrorAction Stop | Out-Null
```
## AP-22 — blind `Set-ExecutionPolicy` as a "fix"
**Symptom**: To silence "running scripts is disabled on this system", the machine-wide policy is flipped to Unrestricted and left open permanently for every user and process.
**Bad**:
```powershell
Set-ExecutionPolicy Unrestricted -Scope LocalMachine -Force; .\setup.ps1
```
**Why it fails**: It dismantles the script-provenance gate for the whole box, demands elevation, fails outright when policy is GPO-managed, and papers over the actual cause: unsigned or Mark-of-the-Web-blocked files.
**Risk**: high | **Related**: SEC-, SAFE-
**Repair**:
```powershell
if ((Get-AuthenticodeSignature .\setup.ps1).Status -ne 'Valid') { throw 'setup.ps1 is unsigned or altered: sign it, do not bypass policy' }; .\setup.ps1
```
## AP-23 — `DownloadString` cradles
**Symptom**: Bootstrap one-liners fetch a script straight into memory and execute it; afterward nobody can say what code ran, whence it came, or whether it changed since yesterday.
**Bad**:
```powershell
iex ((New-Object Net.WebClient).DownloadString('https://example.com/tools/install.ps1'))
```
**Why it fails**: This is the canonical malware cradle: code never touches disk (no review trail, weakened AV/audit signal), executes with your privileges, and trusts whatever the endpoint serves today — hijacks and supply-chain swaps included.
**Risk**: critical | **Related**: SEC-, SAFE-
**Repair**:
```powershell
Invoke-WebRequest $url -OutFile .\install.ps1; Get-AuthenticodeSignature .\install.ps1   # inspect; require Valid before running; prefer Install-Module from PSGallery
```
## AP-24 — disabling TLS/certificate validation to "make it work"
**Symptom**: Facing a self-signed internal endpoint, scripts set the global validation callback to `{ $true }` or pin `SecurityProtocol` down to Ssl3/Tls "just for compatibility".
**Bad**:
```powershell
[Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }; [Net.ServicePointManager]::SecurityProtocol = 'Ssl3'
```
**Why it fails**: The callback switches off certificate validation for EVERY later HTTPS call in the session — logins included — opening a MITM window, while Ssl3/TLS1.0 are obsolete protocols modern servers must refuse.
**Risk**: high | **Related**: SEC-, SAFE-
**Repair**:
```powershell
Import-Certificate -FilePath .\rootCA.cer -CertStoreLocation Cert:\CurrentUser\Root   # fix trust; PS7-only escape hatch: -SkipCertificateCheck on one known test call
```
