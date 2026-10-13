[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$TaskName = "XAUUSD Execution-Disabled Shadow",
    [Parameter(Mandatory = $true)]
    [ValidateSet("STOP-EXECUTION-DISABLED-SHADOW")]
    [string]$ConfirmToken
)

$ErrorActionPreference = "Stop"

$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $Task) {
    [pscustomobject]@{
        status = "NOT_INSTALLED"
        task_name = $TaskName
        service_running = $false
        execution_enabled = $false
        broker_action_count = 0
    } | ConvertTo-Json
    return
}

if (-not $PSCmdlet.ShouldProcess($TaskName, "Stop execution-disabled shadow host")) {
    return
}

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
$Deadline = [DateTime]::UtcNow.AddSeconds(20)
do {
    Start-Sleep -Milliseconds 500
    $Task = Get-ScheduledTask -TaskName $TaskName
} while ($Task.State -eq "Running" -and [DateTime]::UtcNow -lt $Deadline)

if ($Task.State -eq "Running") {
    throw "Shadow task did not stop within the allowed interval."
}

[pscustomobject]@{
    status = "STOPPED"
    task_name = $TaskName
    task_state = [string]$Task.State
    service_running = $false
    execution_enabled = $false
    broker_action_count = 0
} | ConvertTo-Json
