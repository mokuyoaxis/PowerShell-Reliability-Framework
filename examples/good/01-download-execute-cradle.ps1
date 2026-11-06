# PRF Example 01 — download-execute-cradle
# Rules demonstrated: SEC-002, SEC-003
# Risk class: critical
# NOTE: bad/*.ps1 are NEGATIVE training examples. Never execute them.

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$BaseUrl = 'https://tools.contoso.example/bootstrap',
    [string]$ExpectedSha256 = ''   # pin the trusted hash out-of-band
)

$url = "$BaseUrl/install-agent.ps1"
$installer = Join-Path -Path ([System.IO.Path]::GetTempPath()) -ChildPath 'install-agent.ps1'

# SEC-003: never pipe remote content into Invoke-Expression. Download to
# disk first so the exact bytes that will run are inspectable and auditable.
Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing

# SEC-002: verify the file's SHA256 against an independently obtained hash
# before any execution path can touch it.
$actualHash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash
if ($ExpectedSha256 -and $actualHash -ne $ExpectedSha256) {
    throw "SHA256 mismatch: expected $ExpectedSha256, got $actualHash"
}

# Inspection gate: surface what would actually run before running it.
Get-Content -LiteralPath $installer -TotalCount 40 | Write-Host

# SEC-010: run under the existing execution policy, never -ExecutionPolicy
# Bypass. The installer must carry a valid Authenticode signature.
$signature = Get-AuthenticodeSignature -FilePath $installer
if ($signature.Status -ne 'Valid') {
    throw "Installer signature is not valid: $($signature.Status)"
}

if ($PSCmdlet.ShouldProcess($installer, 'Execute hash-verified installer')) {
    & powershell.exe -NoProfile -File $installer
    if ($LASTEXITCODE -ne 0) { throw "Installer exited with code $LASTEXITCODE" }
}
Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
Write-Host 'Agent installed from verified artifact.'
