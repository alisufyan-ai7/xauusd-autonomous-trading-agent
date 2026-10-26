#requires -Version 5.1
<#
Use ONLY from an exact pinned Git commit after native Windows CI.
Updates the existing stopped XAUUSD Exness Pro DEMO task (one writer).
No new scheduled task. Does not disable safeguards or authorize LIVE.
Requires separate owner-attended confirmation, then source and broker checks.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[a-f0-9]{40}$')]
    [string]$SourceCommit,
    [string]$Repo = 'C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent',
    [Parameter(Mandatory=$true)]
    [ValidateSet('RECOVER-PINNED-EXNESS-DEMO-OWNER-ATTENDED')]
    [string]$OwnerApproval
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$TaskName = 'XAUUSD Exness Pro DEMO Autonomous Trader'
$Previous = 'dfd193a4c9a6db00da81b806f2b160892eae30c9'
$Root = Join-Path $env:ProgramData 'XAUUSD-DemoAutonomous'
$Old = Join-Path (Join-Path $Root 'versions') $Previous
$New = Join-Path (Join-Path $Root 'versions') $SourceCommit
$Runner = Join-Path $Root 'run-current.ps1'
$NewPython = Join-Path $New '.venv\Scripts\python.exe'
$OldPython = Join-Path $Old '.venv\Scripts\python.exe'
$State = Join-Path $env:LOCALAPPDATA 'XAUUSD-DemoService'
$Vault = Join-Path (Join-Path $env:LOCALAPPDATA 'XAUUSD-DemoRecoveryEvidence') (
    [datetime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
)

function Confirm-OneStoppedTask {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    if ($task.State -ne 'Ready' -or @($task.Actions).Count -ne 1 -or
        $task.Principal.LogonType -ne 'Interactive' -or
        $task.Actions[0].Arguments -notmatch 'run-current\.ps1') {
        throw 'RECOVERY_HOLD_EXPECTED_ONE_STOPPED_INTERACTIVE_TASK'
    }
    $writers = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        (($_.Name -in @('python.exe','pythonw.exe')) -and
         $_.CommandLine -match 'xauusd_demo\.run_exness_demo' -and
         $_.CommandLine -match '\-\-run') -or
        ($_.Name -eq 'powershell.exe' -and
         $_.CommandLine -match 'run-current\.ps1')
    })
    if ($writers.Count -ne 0) {
        throw 'RECOVERY_HOLD_ANOTHER_TRADER_OR_RUNNER_EXISTS'
    }
    return $task
}

$task = Confirm-OneStoppedTask
$SID = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$owner = [string]$task.Principal.UserId
if ($owner -notmatch '^S-1-') {
    $nt = New-Object Security.Principal.NTAccount -ArgumentList $owner
    $owner = $nt.Translate([Security.Principal.SecurityIdentifier]).Value
}
if ($SID -ne $owner) { throw 'RECOVERY_HOLD_DIFFERENT_TASK_OWNER' }
if (-not [string]::Equals(
    ([string]$task.Actions[0].WorkingDirectory).TrimEnd('\'),
    $Old,[StringComparison]::OrdinalIgnoreCase
)) {
    throw 'RECOVERY_HOLD_WRONG_PREVIOUS_TASK_RELEASE'
}
foreach ($path in @($Repo,$OldPython,$Runner,$State)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw 'RECOVERY_HOLD_EXPECTED_PREVIOUS_RESOURCE_MISSING'
    }
}
$PriorRunner = Get-Content -LiteralPath $Runner -Raw
if (-not $PriorRunner.Contains($Old) -or
    -not $PriorRunner.Contains($OldPython)) {
    throw 'RECOVERY_HOLD_PREVIOUS_RUNNER_NOT_PINNED'
}
if (Test-Path -LiteralPath $New) {
    throw 'RECOVERY_HOLD_NEW_VERSION_ALREADY_STAGED_REVIEW_REQUIRED'
}
$terminals = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
    $_.Name -eq 'terminal64.exe' -and $_.ExecutablePath
})
if ($terminals.Count -ne 1 -or
    $terminals[0].SessionId -ne (Get-Process -Id $PID).SessionId) {
    throw 'RECOVERY_HOLD_ONE_ALREADY_RUNNING_SAME_SESSION_MT5_REQUIRED'
}

Write-Output ('SOURCE_PIN=' + $SourceCommit)
Write-Output 'EXISTING_TASK_ONLY_AND_OWNER_SID_CONFIRMED'

& git -C $Repo fetch --no-tags origin main
if ($LASTEXITCODE -ne 0) { throw 'RECOVERY_HOLD_GIT_FETCH_FAILED' }
$kind = [string](& git -C $Repo cat-file -t $SourceCommit)
if ($LASTEXITCODE -ne 0 -or $kind.Trim() -ne 'commit') {
    throw 'RECOVERY_HOLD_SOURCE_COMMIT_NOT_FOUND'
}
& git -C $Repo merge-base --is-ancestor $SourceCommit FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'RECOVERY_HOLD_SOURCE_NOT_ON_MAIN' }
$archive = Join-Path $env:TEMP ('xauusd-attended-' + $SourceCommit + '.zip')
try {
    & git -C $Repo archive --format=zip --output $archive $SourceCommit
    if ($LASTEXITCODE -ne 0) { throw 'RECOVERY_HOLD_ARCHIVE_FAILED' }
    New-Item -ItemType Directory -Force -Path $New | Out-Null
    Expand-Archive -LiteralPath $archive -DestinationPath $New
} finally {
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
}
$recovery = Join-Path $New 'demo_adapter\scripts\attended_demo_recovery_core.py'
$coordinator = Join-Path $New 'demo_adapter\src\xauusd_demo\continuous_coordinator.py'
if (-not (Test-Path -LiteralPath $recovery) -or
    -not (Test-Path -LiteralPath $coordinator)) {
    throw 'RECOVERY_HOLD_PINNED_CODE_MISSING'
}
# Source archive is pinned to one exact Git commit; validate critical blobs.
foreach ($pair in @(
    @('demo_adapter/scripts/attended_demo_recovery_core.py',$recovery),
    @('demo_adapter/src/xauusd_demo/continuous_coordinator.py',$coordinator)
)) {
    $expected = [string](& git -C $Repo rev-parse ($SourceCommit + ':' + $pair[0]))
    if ($LASTEXITCODE -ne 0) { throw 'RECOVERY_HOLD_PINNED_GIT_BLOB_UNAVAILABLE' }
    $text = [IO.File]::ReadAllText([string]$pair[1])
    $text = $text.Replace(([string][char]13 + [string][char]10),[string][char]10)
    $payload = [Text.Encoding]::UTF8.GetBytes($text)
    $prefix = [Text.Encoding]::ASCII.GetBytes('blob ' + $payload.Length + [char]0)
    $bytes = New-Object byte[] ($prefix.Length + $payload.Length)
    [Buffer]::BlockCopy($prefix,0,$bytes,0,$prefix.Length)
    [Buffer]::BlockCopy($payload,0,$bytes,$prefix.Length,$payload.Length)
    $sha1 = [Security.Cryptography.SHA1]::Create()
    try {
        $actual = ([BitConverter]::ToString($sha1.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()
    } finally { $sha1.Dispose() }
    if ($actual -ne $expected.Trim()) {
        throw 'RECOVERY_HOLD_PINNED_SOURCE_HASH_MISMATCH'
    }
}
& $OldPython -m venv (Join-Path $New '.venv')
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $NewPython)) {
    throw 'RECOVERY_HOLD_VENV_SETUP_FAILED'
}
& $NewPython -m pip --disable-pip-version-check install --no-input --no-cache-dir -e $New -e (Join-Path $New 'demo_adapter') 'tzdata>=2025.2'
if ($LASTEXITCODE -ne 0) { throw 'RECOVERY_HOLD_DEPENDENCY_INSTALL_FAILED' }

# Create private evidence storage; never commit raw SQLite, account or secrets.
New-Item -ItemType Directory -Force -Path $Vault | Out-Null
$acl = Get-Acl -LiteralPath $Vault
$acl.SetAccessRuleProtection($true,$false)
foreach ($sidstr in @($SID,'S-1-5-18','S-1-5-32-544')) {
    $targetSID = New-Object Security.Principal.SecurityIdentifier -ArgumentList $sidstr
    $rule = [Security.AccessControl.FileSystemAccessRule]::new(
        $targetSID,[Security.AccessControl.FileSystemRights]::FullControl,
        [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit',
        [Security.AccessControl.PropagationFlags]::None,
        [Security.AccessControl.AccessControlType]::Allow
    )
    [void]$acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $Vault -AclObject $acl
$task = Confirm-OneStoppedTask

# One temporary read-only broker attachment. Recovery core independently
# proves identity, zero positions/orders/history and fresh XAUUSD twice,
# backs up all existing SQLite journals, then attended-rearms BOTH stores.
$terminalPath = [string]$terminals[0].ExecutablePath
& $NewPython -B $recovery --state $State --vault $Vault --terminal $terminalPath --attended-confirmation $OwnerApproval
if ($LASTEXITCODE -ne 0) {
    throw 'RECOVERY_HOLD_REARM_NOT_AUTHORIZED_OR_BROKER_PROOF_FAILED'
}
Copy-Item -LiteralPath $Runner -Destination (Join-Path $Vault 'runner.before-recovery.ps1')
$updated = $PriorRunner.Replace($OldPython,$NewPython).Replace($Old,$New)
if (-not $updated.Contains($NewPython) -or $updated.Contains($OldPython)) {
    throw 'RECOVERY_HOLD_NEW_RUNNER_REWRITE_FAILED'
}
$task = Confirm-OneStoppedTask
[IO.File]::WriteAllText($Runner,$updated,(New-Object Text.UTF8Encoding($false)))
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -WorkingDirectory $New -Argument (
    '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}"' -f $Runner
)
Set-ScheduledTask -TaskName $TaskName -Action $action -ErrorAction Stop | Out-Null
$task = Confirm-OneStoppedTask
if (-not [string]::Equals(
    ([string]$task.Actions[0].WorkingDirectory).TrimEnd('\'),
    $New,[StringComparison]::OrdinalIgnoreCase
)) { throw 'RECOVERY_HOLD_TASK_ACTION_NOT_NEW_PIN' }

$startedUTC = [datetime]::UtcNow
Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
Write-Output 'EXISTING_DEMO_TASK_RESTART_REQUESTED_NO_SECOND_TASK'

$healthPath = Join-Path $State 'health.json'
$fresh = $false
for ($i=0;$i -lt 40;$i++) {
    Start-Sleep -Seconds 2
    if ((Get-ScheduledTask -TaskName $TaskName).State -ne 'Running') { break }
    if (-not (Test-Path -LiteralPath $healthPath)) { continue }
    try {
        $h = Get-Content -LiteralPath $healthPath -Raw | ConvertFrom-Json
        $t = [datetimeoffset]::Parse([string]$h.utc).UtcDateTime
        if ($t -ge $startedUTC.AddSeconds(-2) -and $h.state -eq 'ACTIVE' -and
            $h.broker_mode -eq 'EXNESS_DEMO_ONLY') {
            $fresh = $true
            Write-Output ('FRESH_HEALTH_UTC=' + $t.ToString('o'))
            Write-Output ('FRESH_HEALTH_ACTION=' + [string]$h.action)
            Write-Output ('FRESH_STRATEGY_STATUS=' + [string]$h.strategy_status)
            break
        }
    } catch { }
}
if (-not $fresh) {
    # Never automatically roll back or stop a writer after startup: exposure
    # may have changed and an acknowledged position must remain supervised.
    Write-Output 'RECOVERY_POSTSTART_HEARTBEAT_UNVERIFIED_NO_AUTOMATIC_ROLLBACK'
    throw 'RECOVERY_POSTSTART_HOLD_NEEDS_BROKER_AND_TASK_REVIEW'
}
Write-Output 'MONITORING_REAL_NEXT_COMPLETED_M15_NO_FORCED_TRADE'
$cycles = Join-Path $State 'cycles.jsonl'
$seen = $false
$until = [datetime]::UtcNow.AddMinutes(17)
while ([datetime]::UtcNow -lt $until) {
    if ((Get-ScheduledTask -TaskName $TaskName).State -ne 'Running') { break }
    if (Test-Path -LiteralPath $cycles) {
        foreach ($line in @(Get-Content -LiteralPath $cycles -Tail 30 -ErrorAction SilentlyContinue)) {
            try {
                $record = $line | ConvertFrom-Json
                $recordTime = [datetimeoffset]::Parse([string]$record.utc).UtcDateTime
                $status = [string]$record.strategy_status
                if ($recordTime -gt $startedUTC -and $status -match '^(MT5_HISTORY_OR_QUOTE_NOT_READY|M15_ALREADY_EVALUATED|M15_HISTORY_CHANGED_DURING_CAPTURE|DEMO_SESSION_OR_NEWS_WINDOW_BLOCKED|MARKET_CONTEXT_|TPB_|QUALIFIED_TPB_WITH_AI_CONFIRMATION|BROKER_SOURCE_BOUND_TPB_ELIGIBLE)') {
                    $seen = $true
                    Write-Output ('COMPLETED_M15_EVIDENCE_UTC=' + $recordTime.ToString('o'))
                    Write-Output ('COMPLETED_M15_EVALUATION_RESULT=' + $status)
                    break
                }
            } catch { }
        }
    }
    if ($seen) { break }
    Start-Sleep -Seconds 8
}
Write-Output ('FINAL_TASK_STATE=' + (Get-ScheduledTask -TaskName $TaskName).State)
Write-Output ('FRESH_M15_EVALUATION_EVIDENCED=' + $seen)
Write-Output ('PRIVATE_RECOVERY_BACKUPS=' + $Vault)
if (-not $seen) { Write-Output 'M15_EVIDENCE_NOT_YET_OBSERVED_DO_NOT_FORCE_ORDER' }
Write-Output 'ATTENDED_EXNESS_DEMO_RECOVERY_SCRIPT_FINISHED_NO_LIVE'
