#requires -Version 5.1
<#
Hide console for EXISTING Exness Pro DEMO scheduled task. Keep exactly the
same service, user session, broker account, task name and SQLite state.
RDP disconnect is supported; Windows logoff is NOT.
#>
[CmdletBinding()]
param(
    [string]$TaskName = 'XAUUSD Exness Pro DEMO Autonomous Trader',
    [string]$SourceCommit = 'efab8be64b97cad464932cf7cf6cac034134e800'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Join-Path $env:ProgramData 'XAUUSD-DemoAutonomous'
$Installed = Join-Path (Join-Path $Root 'versions') $SourceCommit
$Python = Join-Path $Installed '.venv\Scripts\python.exe'
$Runner = Join-Path $Root 'run-current.ps1'
$LogDir = Join-Path $env:LOCALAPPDATA 'XAUUSD-DemoService'

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'Pinned Python runtime missing; no task changed'
}
if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) {
    throw 'Existing service runner missing; no task changed'
}
$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
if ($Task.Actions.Count -ne 1) {
    throw 'Unexpected scheduled task actions; no task changed'
}
$Existing = $Task.Actions[0]
if (
    $Existing.Execute -notmatch '(^|\\)powershell\.exe$' -or
    $Existing.Arguments -notlike '*run-current.ps1*' -or
    $Existing.WorkingDirectory -ne $Installed
) {
    throw 'Unexpected task executable/source; no task changed'
}
$RunnerText = Get-Content -LiteralPath $Runner -Raw
if (
    $RunnerText -notlike "*$Installed*" -or
    $RunnerText -notlike "*$Python*" -or
    $RunnerText -notlike '*run_exness_demo --run*'
) {
    throw 'Runner not pinned to exact installed DEMO; no task changed'
}
if ($Task.Principal.LogonType -ne 'Interactive') {
    throw 'Original task is not using the expected interactive MT5 session'
}

# The current DEMO preflight rejects wrong/LIVE account or ANY exposure.
Write-Host 'VERIFYING_EXACT_DEMO_AND_ZERO_EXPOSURE'
& $Python -u -m xauusd_demo.run_exness_demo --preflight
if ($LASTEXITCODE -ne 0) {
    throw 'DEMO account/flat preflight failed; task NOT changed'
}

$NewAction = New-ScheduledTaskAction -Execute 'powershell.exe' -WorkingDirectory $Installed -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}"' -f $Runner)
Write-Host 'STOPPING_EXISTING_TASK_FOR_HIDDEN_WINDOW_CHANGE'
Stop-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$Stopped = $false
for ($i = 0; $i -lt 40; $i++) {
    if ((Get-ScheduledTask -TaskName $TaskName).State -ne 'Running') {
        $Stopped = $true
        break
    }
    Start-Sleep -Milliseconds 500
}
if (-not $Stopped) {
    throw 'Original task did not stop; no replacement started'
}

# No orphan pinned Python interpreter can coexist with the newly started one.
$Orphan = @()
for ($i = 0; $i -lt 20; $i++) {
    $Orphan = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction Stop | Where-Object {
        $_.ExecutablePath -and
        [string]::Equals([string]$_.ExecutablePath, [string]$Python, [StringComparison]::OrdinalIgnoreCase)
    })
    if ($Orphan.Count -eq 0) { break }
    Start-Sleep -Milliseconds 500
}
if ($Orphan.Count -gt 0) {
    throw 'Old Python process survived stop; no second writer started'
}

Set-ScheduledTask -TaskName $TaskName -Action $NewAction -ErrorAction Stop | Out-Null
$Updated = Get-ScheduledTask -TaskName $TaskName
if ($Updated.Actions.Count -ne 1 -or
    $Updated.Actions[0].Arguments -notlike '*-WindowStyle Hidden*') {
    throw 'Hidden launch option not persisted; task not restarted'
}

Write-Host 'RESTARTING_EXISTING_DEMO_TASK_WITH_HIDDEN_CONSOLE'
Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
Start-Sleep -Seconds 5
$FinalTask = Get-ScheduledTask -TaskName $TaskName
$FinalInfo = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host ('TASK_STATE={0}' -f $FinalTask.State)
Write-Host ('TASK_LAST_RESULT={0}' -f $FinalInfo.LastTaskResult)
Write-Host ('HIDDEN_TASK_ACTION={0}' -f $FinalTask.Actions[0].Arguments)
Write-Host ('PINNED_BUILD={0}' -f $SourceCommit)
Write-Host 'SAME_TASK__NO_NEW_ACTIVATION__NO_LIVE_TRADING'
$Console = Join-Path $LogDir 'service-console.log'
$Cycles = Join-Path $LogDir 'cycles.jsonl'
if (Test-Path -LiteralPath $Console) {
    Write-Host '=== RECENT CONSOLE ==='
    Get-Content -LiteralPath $Console -Tail 12
}
if (Test-Path -LiteralPath $Cycles) {
    Write-Host '=== RECENT CYCLES ==='
    Get-Content -LiteralPath $Cycles -Tail 8
}
if ($FinalTask.State -ne 'Running') {
    throw 'Hidden task not Running; inspect console above'
}
