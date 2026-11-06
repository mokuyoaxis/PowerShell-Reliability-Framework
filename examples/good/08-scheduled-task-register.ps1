# PRF Example 08 — scheduled-task-register
# Rules demonstrated: IDEM-009, SEC-010
# Risk class: medium
# NOTE: bad/*.ps1 are NEGATIVE training examples. Never execute them.

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$TaskName   = 'NightlyCleanup',
    [string]$ScriptPath = 'C:\Program Files\Contoso\bin\cleanup.ps1'
)

# Verify the payload BEFORE wiring a schedule to it: a task pointing at a
# missing file fails quietly, night after night.
if (-not (Test-Path -LiteralPath $ScriptPath -PathType Leaf)) {
    throw "Action script not found: $ScriptPath"
}

# SEC-010: the task runs under the existing execution policy, never
# -ExecutionPolicy Bypass, so the payload must be validly signed.
$signature = Get-AuthenticodeSignature -FilePath $ScriptPath
if ($signature.Status -ne 'Valid') {
    throw "Action script signature is not valid: $($signature.Status)"
}

# IDEM-009: overwrite-AWARENESS. Inspect any existing registration first;
# never silently clobber a task someone else may depend on.
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    $currentAction = $existing.Actions[0].Execute
    if ($currentAction -like '*cleanup.ps1*') {
        Write-Host "Task '$TaskName' already points at '$currentAction'. Nothing to do."
    } else {
        Write-Warning "Task '$TaskName' exists with action '$currentAction'; refusing to overwrite. Review manually."
    }
    return
}

if ($PSCmdlet.ShouldProcess($TaskName, "Register daily 02:30 task -> $ScriptPath")) {
    $action   = New-ScheduledTaskAction -Execute 'powershell.exe' `
        -Argument "-NoProfile -File `"$ScriptPath`""
    $trigger  = New-ScheduledTaskTrigger -Daily -At '02:30'
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    Register-ScheduledTask -TaskName $TaskName -Action $action `
        -Trigger $trigger -Settings $settings | Out-Null
    Write-Host "Registered task '$TaskName'."
}
