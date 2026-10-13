[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$InstallRoot = "C:\ProgramData\XAUUSD-Agent",
    [string]$TaskName = "XAUUSD Execution-Disabled Shadow",
    [Parameter(Mandatory = $true)]
    [ValidateSet("START-EXECUTION-DISABLED-SHADOW")]
    [string]$ConfirmToken
)

$ErrorActionPreference = "Stop"

function Resolve-Python312 {
    $Launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($Launcher) {
        $Candidate = (& $Launcher.Source -3.12 -c "import sys; print(sys.executable)").Trim()
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
            return $Candidate
        }
    }

    $Python = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $Python) {
        throw "Python 3.12 is not available."
    }
    $Version = (& $Python.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
    if ($LASTEXITCODE -ne 0 -or $Version -ne "3.12") {
        throw "Python 3.12 is required; resolved version: $Version"
    }
    return $Python.Source
}

function Set-RestrictedDirectoryAcl([string]$Path) {
    $Identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    if ($null -eq $Identity.User) {
        throw "Current Windows identity has no SID."
    }

    $Acl = New-Object System.Security.AccessControl.DirectorySecurity
    $Acl.SetAccessRuleProtection($true, $false)

    $Inheritance = [System.Security.AccessControl.InheritanceFlags]"ContainerInherit, ObjectInherit"
    $Propagation = [System.Security.AccessControl.PropagationFlags]::None
    $Allow = [System.Security.AccessControl.AccessControlType]::Allow
    $Rights = [System.Security.AccessControl.FileSystemRights]::FullControl

    foreach ($SidValue in @(
        $Identity.User.Value,
        "S-1-5-18",
        "S-1-5-32-544"
    )) {
        $Sid = New-Object System.Security.Principal.SecurityIdentifier($SidValue)
        $Rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $Sid,
            $Rights,
            $Inheritance,
            $Propagation,
            $Allow
        )
        $Acl.AddAccessRule($Rule)
    }

    Set-Acl -LiteralPath $Path -AclObject $Acl
}

$ActiveMarker = Join-Path $InstallRoot "active-release.txt"
if (-not (Test-Path -LiteralPath $ActiveMarker -PathType Leaf)) {
    throw "Active release marker is missing."
}

$ReleaseId = (Get-Content -LiteralPath $ActiveMarker -Raw).Trim()
if ($ReleaseId -notmatch "^[A-Za-z0-9._-]+$") {
    throw "Active release identifier is invalid."
}

$ReleaseRoot = Join-Path (Join-Path $InstallRoot "releases") $ReleaseId
if (-not (Test-Path -LiteralPath $ReleaseRoot -PathType Container)) {
    throw "Active release directory is missing."
}

$Preflight = Join-Path $ReleaseRoot "deploy\windows\Test-ExecutionDisabledCandidate.ps1"
& $Preflight -ReleaseRoot $ReleaseRoot | Out-Null

$Wheels = @(Get-ChildItem -LiteralPath (Join-Path $ReleaseRoot "package") -Filter "*.whl" -File)
if ($Wheels.Count -ne 1) {
    throw "Exactly one sealed wheel is required."
}
$Wheel = $Wheels[0].FullName

$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    throw "Scheduled task already exists: $TaskName"
}

$SystemPython = Resolve-Python312
$RuntimeRoot = Join-Path (Join-Path $InstallRoot "runtime") $ReleaseId
$StateRoot = Join-Path $InstallRoot "state"
New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
New-Item -ItemType Directory -Path $StateRoot -Force | Out-Null
Set-RestrictedDirectoryAcl $RuntimeRoot
Set-RestrictedDirectoryAcl $StateRoot

$Venv = Join-Path $RuntimeRoot ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
    & $SystemPython -m venv --system-site-packages $Venv
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Python 3.12 virtual environment."
    }
}

& $VenvPython -m pip install --disable-pip-version-check --no-input --no-deps $Wheel
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install sealed candidate wheel."
}

$BridgeVersion = (& $VenvPython -c "import MetaTrader5 as m; print(m.__version__)").Trim()
if ($LASTEXITCODE -ne 0 -or $BridgeVersion -ne "5.0.6090") {
    throw "MetaTrader5 bridge must be exactly 5.0.6090; observed: $BridgeVersion"
}

$StaticJson = (& $VenvPython -m xauusd_agent.cli --state-directory $StateRoot --print-preflight).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Static execution-disabled preflight failed."
}
$Static = $StaticJson | ConvertFrom-Json
if ($Static.execution_enabled -ne $false -or [int]$Static.broker_action_count -ne 0) {
    throw "Static preflight did not preserve zero execution capability."
}
if ($Static.analyst_transport -ne "DISABLED") {
    throw "Analyst transport must remain disabled."
}

$BrokerJson = (& $VenvPython -m xauusd_agent.cli --state-directory $StateRoot --broker-preflight).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Live MT5 broker preflight failed."
}
$Broker = $BrokerJson | ConvertFrom-Json
if (
    $Broker.trading_api_disabled -ne $true -or
    [int]$Broker.open_positions -ne 0 -or
    [int]$Broker.pending_orders -ne 0 -or
    $Broker.execution_enabled -ne $false -or
    [int]$Broker.broker_action_count -ne 0
) {
    throw "Live broker preflight did not satisfy PCR-3 execution-disabled requirements."
}

if (-not $PSCmdlet.ShouldProcess($TaskName, "Register and start execution-disabled shadow host")) {
    return
}

$UserId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Arguments = '-m xauusd_agent.cli --state-directory "{0}" --run-service --interval-seconds 15' -f $StateRoot
$Action = New-ScheduledTaskAction -Execute $VenvPython -Argument $Arguments -WorkingDirectory $RuntimeRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $UserId
$Principal = New-ScheduledTaskPrincipal -UserId $UserId -LogonType Interactive -RunLevel Highest
$SettingsArgs = @{
    StartWhenAvailable = $true
    RestartCount = 3
    RestartInterval = (New-TimeSpan -Minutes 1)
    MultipleInstances = "IgnoreNew"
    ExecutionTimeLimit = (New-TimeSpan -Seconds 0)
}
$Settings = New-ScheduledTaskSettingsSet @SettingsArgs
$RegisterArgs = @{
    TaskName = $TaskName
    Action = $Action
    Trigger = $Trigger
    Principal = $Principal
    Settings = $Settings
}
Register-ScheduledTask @RegisterArgs | Out-Null

try {
    Start-ScheduledTask -TaskName $TaskName

    $HeartbeatPath = Join-Path $StateRoot "heartbeat.json"
    $Deadline = [DateTime]::UtcNow.AddSeconds(45)
    $Heartbeat = $null
    while ([DateTime]::UtcNow -lt $Deadline) {
        Start-Sleep -Seconds 1
        if (Test-Path -LiteralPath $HeartbeatPath -PathType Leaf) {
            try {
                $Candidate = Get-Content -LiteralPath $HeartbeatPath -Raw | ConvertFrom-Json
                if (
                    $Candidate.execution_enabled -eq $false -and
                    [int]$Candidate.broker_action_count -eq 0
                ) {
                    $Heartbeat = $Candidate
                    break
                }
            }
            catch {
            }
        }
    }

    if ($null -eq $Heartbeat) {
        $Task = Get-ScheduledTask -TaskName $TaskName
        $Info = Get-ScheduledTaskInfo -TaskName $TaskName
        throw "Shadow heartbeat did not become healthy. TaskState=$($Task.State) LastTaskResult=$($Info.LastTaskResult)"
    }

    [pscustomobject]@{
        status = "RUNNING"
        release_id = $ReleaseId
        task_name = $TaskName
        state_root = $StateRoot
        heartbeat_utc = $Heartbeat.observed_at
        runtime_state = $Heartbeat.runtime_state
        execution_enabled = $false
        broker_action_count = 0
        analyst_transport_enabled = $false
        alert_delivery_enabled = $false
    } | ConvertTo-Json
}
catch {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    throw
}
