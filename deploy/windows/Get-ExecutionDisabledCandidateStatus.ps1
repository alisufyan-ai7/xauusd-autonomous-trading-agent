[CmdletBinding()]
param(
    [string]$InstallRoot = "C:\ProgramData\XAUUSD-Agent",
    [string]$TaskName = "XAUUSD Execution-Disabled Shadow"
)

$ErrorActionPreference = "Stop"

$ActiveMarker = Join-Path $InstallRoot "active-release.txt"
$ReleaseId = $null
if (Test-Path -LiteralPath $ActiveMarker -PathType Leaf) {
    $ReleaseId = (Get-Content -LiteralPath $ActiveMarker -Raw).Trim()
}

$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
$TaskInfo = $null
if ($Task) {
    $TaskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
}

$HeartbeatPath = Join-Path (Join-Path $InstallRoot "state") "heartbeat.json"
$Heartbeat = $null
$HeartbeatAgeSeconds = $null
if (Test-Path -LiteralPath $HeartbeatPath -PathType Leaf) {
    $Heartbeat = Get-Content -LiteralPath $HeartbeatPath -Raw | ConvertFrom-Json
    if ($Heartbeat.execution_enabled -ne $false -or [int]$Heartbeat.broker_action_count -ne 0) {
        throw "Heartbeat violates the execution-disabled boundary."
    }
    if ($Heartbeat.observed_at) {
        $Observed = [DateTimeOffset]::Parse([string]$Heartbeat.observed_at)
        $HeartbeatAgeSeconds = [math]::Round(
            ([DateTimeOffset]::UtcNow - $Observed.ToUniversalTime()).TotalSeconds,
            3
        )
    }
}

[pscustomobject]@{
    active_release = $ReleaseId
    task_name = $TaskName
    task_installed = ($null -ne $Task)
    task_state = if ($Task) { [string]$Task.State } else { "ABSENT" }
    last_task_result = if ($TaskInfo) { [int]$TaskInfo.LastTaskResult } else { $null }
    heartbeat_present = ($null -ne $Heartbeat)
    heartbeat_age_seconds = $HeartbeatAgeSeconds
    runtime_state = if ($Heartbeat) { [string]$Heartbeat.runtime_state } else { $null }
    open_positions = if ($Heartbeat) { [int]$Heartbeat.open_positions } else { $null }
    pending_orders = if ($Heartbeat) { [int]$Heartbeat.pending_orders } else { $null }
    execution_enabled = $false
    broker_action_count = 0
} | ConvertTo-Json
