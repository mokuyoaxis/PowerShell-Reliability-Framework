# Here-Strings and Heredocs: The Interpreter Boundary (HD Rules)

The other five categories reason about a script that already exists as a file on
disk. Everything in this category happens **before** that assumption is true: the
bytes an agent emits still have to become a PowerShell parse, survive a quoting
boundary, and be written somewhere as a specific number of bytes. That boundary
is where "the code looks right" stops meaning anything, and it is where a large
share of AI-generated PowerShell fails on Windows.

This document is organized around what the parser and the runtime actually do,
not what the documentation implies. Every table below was measured on
Windows PowerShell 5.1.26100.8115 (Desktop) and PowerShell 7.6.5 (Core) in a
single pass; where the two runtimes disagree the disagreement is stated, because
that is the whole point.

## 1. Why This Is A Separate Axis

A model trained on shell tooling reaches for one construct to hand a multi-line
block to something: a heredoc. In bash that is `<<EOF ... EOF`. In PowerShell the
construct is a here-string, `@'...'@`. The two share a name family and an
intention, and they have completely different grammars, so the failure mode is
not "the model wrote wrong PowerShell" — it is "the model wrote the wrong
language's construct and got a plausible-looking error instead of a clear one".

The corpus therefore splits this axis into three questions, each with its own
rules:

| Question | Failure looks like | Rules |
|---|---|---|
| Is the multi-line literal *shaped* correctly? | whole-file parse error | HD-001, HD-002, HD-008 |
| Is the construct *from the right language*? | redirection or operator error, nothing runs | HD-003 |
| Does the payload *arrive* as the bytes you meant? | UTF-16LE file, a BOM, mixed line endings, an empty read | HD-004, HD-005, HD-006, HD-007, HD-009 |

The second and third rows are the ones that are nearly impossible to diagnose from
the transcript, because the operation that went wrong reports success.

## 2. The Here-String Grammar, As The Parser Enforces It

There is no dedicated here-string AST node. A here-string is a
`StringConstantExpressionAst` whose `Kind` property is `Heredoc`; there is
nothing to query for the two delimiters individually. What there is, is a set of
position rules that the scanner enforces before anything else.

Measured on both runtimes, with identical results:

| Construct | Parse errors | Parser message |
|---|---|---|
| `@'` then body then `'@` at column one | 0 | — |
| `@'` followed by one space, then the body | 0 | legal: trailing whitespace is allowed |
| `'@` followed by a space or a statement on the same line | 0 | legal: anything may follow the close delimiter |
| `@'` followed by `# comment` | 1–2 | `No characters are allowed after a here-string header but before the end of line` |
| `@'` followed by `; $x = 1` | 2 | same as above |
| `'@` with four leading spaces | 1 | `White space is not allowed before the string terminator.` |
| `'@` with one leading space | 1 | same |
| `'@` with a leading tab | 1 | same |
| `@''@` on a single line | 1 | header rule |
| `@'` with no close delimiter | 1 | `The string is missing the terminator: '@.` |
| `'@` with no open delimiter | 1 | `The string is missing the terminator: '.` |
| `@'  # note` | 2 | header rule |

Three things in that table are worth keeping in mind, because they are the ones
that do not match the popular summary of the rule.

**Trailing whitespace on the open line is legal.** The common formulation is
"`@'` must be the last thing on the line", which is wrong. A single space after
the header parses cleanly on both runtimes. The rule is: *no characters*, where
whitespace does not count. This matters because a formatter that strips trailing
whitespace can turn a working script into a broken one, and the person who wrote
it will never understand why — HD-002.

**Anything may follow the close delimiter.** `'@` can be immediately followed by
a pipe, a concatenation, a comment or a semicolon statement, all with zero parse
errors. Measured:

```powershell
@'
body
'@ | Set-Content out.json     # 0 parse errors

@'
body
'@ + 'tail'                   # 0 parse errors

$x = @'                       # assignment on the header line: 0 parse errors
body
'@
```

Only the close delimiter's *leading* whitespace is forbidden. So the actual
asymmetry is: the open line may have trailing whitespace but no characters, and
the close line must have no leading whitespace but may have anything after it —
HD-001 and HD-002.

**Line endings are irrelevant to the delimiters.** A here-string body written
CRLF, a close line written CRLF, a mix of the two — all zero parse errors on both
runtimes. CRLF is not the problem here; it shows up later, at the file sink, in
§6.

One message deserves special attention. A stray `'@` with no matching open
delimiter reports `The string is missing the terminator: '.` — the parser prints
the single quote and drops the `@`. When you are searching the transcript for the
offending text, searching for `'@` will not match the error.

## 3. The Bash Heredoc Collision

`<<EOF` does not exist in PowerShell, and the failure is misleading in a specific
way: `<<` is tokenized as *input redirection*. So a block copied from shell
tooling is not rejected as an unknown construct — it is parsed as a redirection
statement looking for a file.

| Pasted into PowerShell | Errors | First message |
|---|---|---|
| `cmd <<EOF` then body then `EOF` | 3 | `Missing file specification after redirection operator.` |
| `cmd <<'EOF'` (quoted form) | 3 | same |
| `$x = <<EOF` then body then `EOF` | 1 | `The '<' operator is reserved for future use.` |

Nothing executes, and the error names a missing file. A reader working from the
error goes looking for the file, or at a redirection they never wrote, and the
real cause — a construct imported from a different shell — stays invisible. That
is HD-003, and the fix is a here-string assigned to a variable, or a payload
written to a file with its path passed in:

```powershell
$payload = @'
Get-Date
'@
$payload | Out-String
```

The same collision shows up in prose too. If a snippet is meant to run in a POSIX
shell and contains a here-string, the here-string's delimiters will look like
garbage to the shell reader and the shell's `$var` expansion will run first (see
§5.2). Keep the two files apart rather than mixing them in one fenced block.

## 4. A Legal Multi-Line String That Is Still A Trap

A single-quoted string may contain a literal newline, on both runtimes, with zero
parse errors:

```powershell
$banner = '
continued on the following line'
```

It parses. It also survives every static gate in the pipeline, because it is
syntactically valid. It only misbehaves when a formatter, a linter, a reviewer or
a subsequent edit reflows the block and silently changes the string's content.
Multi-line payloads belong in a here-string, where the boundary is explicit and
cannot be moved by reflow — HD-008.

The detection pattern covers only the form where the newline immediately follows
the opening quote; a newline buried in the middle of a long single-quoted string
needs AST inspection, which is the v0.2 work the self-test already flags for the
contextual `IDEM` detectors.

## 5. What A Here-String Costs You At Runtime

Everything in this section is byte-level measurement, not documentation reading.
The payload in every case was the same four-line JSON here-string.

### 5.1 The encoding table

| Sink | PowerShell 7.6.5 | Windows PowerShell 5.1 |
|---|---|---|
| `Set-Content` (no `-Encoding`) ¹ | 41 B, no BOM | 41 B, no BOM (ANSI codepage) |
| `Out-File` (no `-Encoding`) | 41 B, no BOM | **84 B, `FF FE` BOM, 41 NUL bytes (UTF-16LE)** |
| `Set-Content -Encoding UTF8` | 41 B, no BOM | **44 B, `EF BB BF` BOM** |
| `Set-Content -Encoding Unicode` | 84 B, UTF-16LE | 84 B, UTF-16LE |
| `Set-Content -Encoding ASCII` | 41 B, no BOM | 41 B, no BOM |
| `Set-Content -Encoding OEM` | 41 B, no BOM | 41 B, no BOM |
| `[IO.File]::WriteAllText` + `UTF8Encoding($false)` | **39 B, no BOM, 0 CR, 3 LF** | **39 B, no BOM, 0 CR, 3 LF** |
| `Add-Content` (no `-Encoding`) ² | 41 B, no BOM | 41 B, no BOM (ANSI codepage) |
| `[IO.File]::WriteAllText` + `UTF8Encoding($true)` ² | 42 B, `EF BB BF` BOM | 42 B, `EF BB BF` BOM |

¹ The "ANSI codepage" rows are payload-dependent. The four-line JSON payload is
pure ASCII, so the byte counts match; non-ASCII content does not survive
unchanged. Without `-Encoding`, `Set-Content` and `Add-Content` on 5.1 encode
through the host's ANSI codepage, so the same command writes different bytes on
hosts with different locales. Measured in issue #2 on a `gb2312` host with the
payload `caf` + U+00E9: 5.1 wrote 7 B `63 61 66 A8 A6 0D 0A` (`A8 A6` is `é` in
GBK), 7.6 wrote 7 B `63 61 66 C3 A9 0D 0A`, for both cmdlets. Same length, no
marker, different bytes — and characters outside the host codepage are lost.
`Set-Content -Encoding UTF8` on 5.1 wrote 10 B `EF BB BF 63 61 66 C3 A9 0D 0A`
on the same host: marked, but locale-independent.

² Rows added from the real-Windows run in issue #2 (Windows PowerShell
5.1.26100.9549, PowerShell 7.6.6); every original row reproduced there unchanged.

COMP-009 is correct that an explicit `-Encoding` is required, and it is correct
that 5.1's `Out-File` defaults to UTF-16LE. What it cannot say, because it stops
at the cmdlet, is that **the recommended fix still diverges**: `-Encoding UTF8`
on 5.1 writes a three-byte `EF BB BF` marker that PowerShell 7 does not write.
Two hosts that were both told to be explicit still produce files that differ by
exactly those three bytes, and the strict consumers that break on a marker —
`jq`, `json.load`, a SHA-256 comparison against a reference — are exactly the
consumers an agent writes manifests for. That is HD-004, and it is the one rule
in this category that is a refinement of an existing one rather than a new fact.

### 5.2 The transport layer

When the script is not already a file, quoting decides whether the bytes survive.
Measured through Git Bash calling `pwsh`:

| Transport | Result |
|---|---|
| `.ps1` written via a **quoted** heredoc delimiter `<<'PSEOF'`, run with `-File` | 3 backslashes intact, literal path intact |
| `.ps1` written via an **unquoted** heredoc delimiter `<<PSEOF`, run with `-File` | `$path`, `$bs` and `$_` all expanded to empty; file written, then `ParserError: An expression was expected after '('.` |
| `pwsh -Command "$MSG"` from a POSIX shell | `$LASTEXITCODE` expanded by bash before PowerShell sees it |
| `pwsh -Command "$MSG"` with `\$` escaped | `$LASTEXITCODE` also empty — legitimately, because no native command ran |
| heredoc used as the only stdin of `python -c` | 30 bytes delivered |
| pipe used as stdin of `python -c` | 30 bytes delivered |
| heredoc delivering a script **and** a payload on the same stdin | **0 bytes** for the payload |
| `pwsh -Command -` reading a script from stdin | works |
| `pwsh -Command` with `$input` piped from a heredoc | works |

Three of those rows are the rules.

The unquoted heredoc row is HD-006 and it is the most expensive one in the
category: the write succeeds, its exit status is zero, and the defect surfaces as
a parse error in the *child* script, which is a different file in a different
process and looks nothing like quoting. The mangled source on disk reads:

```
 = 'C:\Users\MECHREVO\Downloads'
 = (.ToCharArray() | Where-Object {  -eq [char]92 }).Count
```

Every `$` survived. Every identifier attached to a `$` did not.

The `-Command` row is HD-005, and its control case is the part that makes it
undetectable from output: an empty `$LASTEXITCODE` is also the *correct* value
immediately after no native command has run. So "bash ate my variable" and "the
variable is genuinely empty" print the identical string. The two processes even
have different PIDs (7264 versus 10368 in the same probe run), which is why a
careless diff of the two outputs shows nothing. The fix is to quote the whole
argument at the outer shell, or escape every dollar sign, and to prefer `-File`
with a script file for anything longer than a statement.

The stdin row is HD-007. Piping a program's source through stdin and expecting the
same stream to also deliver data returns zero bytes, with no error and no
diagnostic — the interpreter consumes the source and the payload read comes back
empty, which the caller reads as "the payload was absent" rather than "the payload
was never delivered". Keep the two concerns apart: write the script to a file and
invoke it by path, or pass the program with `-c` and feed only the payload on
stdin.

## 6. Line Endings In Generated Artifacts

The parse-time story in §2 says line endings do not matter for delimiters. The
write-time story is different, and it is silent.

The here-string body carries the line feed bytes exactly as they appear in the
source file, which in this repository is a plain `0A`. `Set-Content`, `Out-File`
and `Add-Content` then append their own carriage-return-line-feed terminator to
the final line. Measured byte counts for the same four-line payload through every
cmdlet sink: `cr = 1`, `lf = 4`. The body contributed four line feeds; the cmdlet
contributed one carriage return. The artifact has mixed line endings and one
trailing CRLF that the payload never contained.

Nothing functional notices. It parses as valid JSON, `ConvertFrom-Json` accepts
it, and the script exits zero. The damage shows up only in a checksum comparison
against a reference, in a diff that shows one unexpected line, or in a downstream
consumer that normalizes line endings and then does not hash-match. That is
HD-009, and the fix is the same as HD-004's: assign the payload to a variable and
serialize it explicitly.

## 7. The Canonical Writer

Both encoding and line-ending problems have one solution, and it is the only
sink in §5.1 whose output was byte-identical across the two runtimes:

```powershell
$payload = @'
{
  "service": "svc-01",
  "ok": true
}
'@
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText('C:/temp/manifest.json', $payload, $utf8NoBom)
```

39 bytes, no marker, zero carriage returns, three line feeds — the exact payload,
on 5.1 and on 7.6. The parameterless constructor (`[System.Text.UTF8Encoding]::new()`
or `New-Object System.Text.UTF8Encoding`) writes no marker either; the objects
that do are the static `[System.Text.Encoding]::UTF8` and `UTF8Encoding($true)`,
both with a three-byte preamble on 5.1 and 7.6 (issue #2). Pass `$false` anyway
so the intent is explicit, and never "make it explicit" by switching to
`[System.Text.Encoding]::UTF8` — that is the change that brings the marker back.
Keep the distinction straight: a `.ps1` file that
contains non-ASCII must carry a BOM so that Windows PowerShell 5.1 does not decode
it as the system codepage, but the *payload* written by this call must not get one
— adding a BOM here is what breaks the byte-identical guarantee.

Two notes on scope, because this method is tempting:

- `WriteAllText` overwrites without asking. SAFE-004 and SAFE-005 still apply;
  snapshot the target before overwriting when the write is not the first one.
- `-NoNewline` on a cmdlet sink removes the trailing terminator but does not fix
  the encoding, so it is not a substitute.

## 8. Pre-Flight Checklist

Run this before presenting or executing anything in this category. All of it is
cheap; none of it is guessable.

```powershell
# which engine am I in, and what will it write by default?
$PSVersionTable.PSVersion, $PSVersionTable.PSEdition

# will my writer produce the bytes I intend?
$s = "line1`nline2"
Set-Content C:\temp\probe_a $s
($s | Out-File C:\temp\probe_b)
Compare-Object (Get-Content C:\temp\probe_a -Raw) (Get-Content C:\temp\probe_b -Raw)

# does my heredoc terminator sit at column one?
Select-String -Path .\script.ps1 -Pattern "^[ \t]+['`"]@"   # HD-001
Select-String -Path .\script.ps1 -Pattern "^(?![ \t]*#).*?@['`"][ \t]*[^\s\r\n]"  # HD-002
Select-String -Path .\script.ps1 -Pattern "<<"               # HD-003

# is anything reaching an interpreter through a shell quoting layer?
Select-String -Path .\*.ps1 -Pattern '-Command\s+"[^"\n]*\$[A-Za-z_]'  # HD-005
```

For §5.2 the probe belongs in the shell, not in PowerShell, because the defect is
created before PowerShell starts:

```sh
# does the delimiter stay quoted through the hand-off?
cat > child.ps1 <<'PSEOF'
Write-Output $LASTEXITCODE
PSEOF
pwsh -NoProfile -File child.ps1
```

If the child prints something other than what the child source says, the hand-off
is corrupt, and the fix is the delimiter quote.

## 9. How These Rules Were Established

The nine HD rules were authored from measurement rather than from recall, because
the two things that make this category hard are exactly the two things that
documentation gets wrong or leaves vague: the delimiter grammar, and the byte
format of the sink.

Method: every candidate construct was written as its own `.ps1`, parsed through
`[System.Management.Automation.Language.Parser]` under both runtimes, and recorded
with error count, message, and AST node class. Nothing in the probe set was ever
executed. Runtime behavior was then measured by writing the payload through each
sink and reading the resulting bytes back, counting NULs, carriage returns and
line feeds and inspecting the first eight bytes for a marker. The transport
measurements were taken through Git Bash calling both engines, with the results
written to files and read back, because the host's stdout channel is not
reliable enough to trust for this.

The detection patterns were checked for precision the same way the corpus's own
self-test checks them: each one must match its own `bad` snippet and must not
match its own `good` snippet. All nine are precise rather than contextual, which
is the stronger form and means none of them need the v0.2 AST gate that the
`IDEM` rules are waiting on. Issue #2 found the limit of that check: HD-002's
pattern also fired on a comment line that merely mentions the header
(`examples/good/12`, line 23), which the comment-free snippets could not show.
The pattern now skips comment-only lines while still matching a comment after
the header (`@' # note`), and `tools/rule-selftest.py` carries both cases plus
the `good/12` file as regression checks. A trailing comment on a code line that
mentions `@'` can still trip it.

One finding corrected an assumption made while authoring this. The initial draft
of the delimiter rule was the familiar "`@'` must be the last thing on its
line". The probe showed a single trailing space parses cleanly, so the rule was
rewritten to the narrower and correct "no characters", and the description now
warns that a trailing-whitespace stripper can introduce the fault.
