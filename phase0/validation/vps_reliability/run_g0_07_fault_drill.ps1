param(
  [string]$Output = "C:\Gate0Private\VpsFaultMatrix-R19",
  [ValidatePattern("^$|^[0-9a-f]{64}$")][string]$CompatibilitySha256 = "",
  [switch]$ResumeAfterWindowsRestart
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$FrozenEvents = @(
  "BASELINE", "DISCONNECT", "RECONNECT", "PYTHON_RESTART",
  "MT5_RESTART", "WINDOWS_RESTART", "CLOCK_CHECK", "BUILD_CHECK"
)
$ScenarioIds = @{
  DISCONNECT      = "VPS-R31-DISCONNECT-1"
  RECONNECT       = "VPS-R31-RECONNECT-1"
  PYTHON_RESTART  = "VPS-R31-PYTHON-RESTART-1"
  MT5_RESTART     = "VPS-R31-MT5-RESTART-1"
  WINDOWS_RESTART = "VPS-R31-WINDOWS-RESTART-1"
  CLOCK_CHECK     = "VPS-R31-CLOCK-CHECK-1"
  BUILD_CHECK     = "VPS-R31-BUILD-CHECK-1"
}
$ResumeTaskName = "XAUUSD-G0-07-R31-Resume"
$NetworkWatchdogTaskName = "XAUUSD-G0-07-R31-Network-Reenable"
$ScriptPath = $MyInvocation.MyCommand.Path
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$Private = [System.IO.Path]::GetFullPath($Output)
$CheckpointPath = Join-Path $Private "g0_07_orchestrator_checkpoint.json"
$SafeSummaryPath = Join-Path $Private "G0_07_PUBLICATION_SAFE_SUMMARY.json"
$ProbeChainPath = Join-Path $Private "vps_probe_records.jsonl"

function Assert-Administrator {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = [Security.Principal.WindowsPrincipal]::new($identity)
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "FAIL CLOSED: run this one command from an elevated PowerShell console."
  }
}

function Invoke-PythonJson {
  param([Parameter(Mandatory=$true)][string[]]$Arguments)
  $lines = @(& py -3.12 @Arguments 2>&1 | ForEach-Object { $_.ToString() })
  $exitCode = $LASTEXITCODE
  $text = $lines -join "`n"
  if ($exitCode -ne 0) { throw "FAIL CLOSED: Python command exited $exitCode. $text" }
  try { return ($lines[-1] | ConvertFrom-Json -ErrorAction Stop) }
  catch { throw "FAIL CLOSED: Python command did not return a JSON result. $text" }
}

function Save-Checkpoint {
  param([Parameter(Mandatory=$true)][string]$State, [hashtable]$Values = @{})
  $body = [ordered]@{
    schema = "gate0-vps-fault-orchestrator-checkpoint-1.0"
    state = $State
    updated_utc = (Get-Date).ToUniversalTime().ToString("o")
    repository_head = (& git rev-parse HEAD).Trim()
    private_output = $Private
  }
  if (Test-Path -LiteralPath $CheckpointPath -PathType Leaf) {
    $previous = Get-Content -LiteralPath $CheckpointPath -Raw | ConvertFrom-Json -ErrorAction Stop
    foreach ($property in $previous.PSObject.Properties) {
      if (-not $body.Contains($property.Name)) { $body[$property.Name] = $property.Value }
    }
  }
  foreach ($key in $Values.Keys) { $body[$key] = $Values[$key] }
  $temporary = "$CheckpointPath.tmp"
  $body | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $temporary -Encoding UTF8
  Move-Item -LiteralPath $temporary -Destination $CheckpointPath -Force
}

function Read-Checkpoint {
  if (-not (Test-Path -LiteralPath $CheckpointPath -PathType Leaf)) { return $null }
  return (Get-Content -LiteralPath $CheckpointPath -Raw | ConvertFrom-Json -ErrorAction Stop)
}

function Get-ProbeEvents {
  if (-not (Test-Path -LiteralPath $ProbeChainPath -PathType Leaf)) {
    throw "FAIL CLOSED: accepted private baseline chain is missing."
  }
  return @(Get-Content -LiteralPath $ProbeChainPath | Where-Object { $_.Trim() } |
    ForEach-Object { ($_ | ConvertFrom-Json -ErrorAction Stop).event })
}

function Assert-ExactPrefix {
  $result = Invoke-PythonJson -Arguments @(
    (Join-Path $PSScriptRoot "verify_private_matrix.py"),
    "--output", $Private, "--allow-incomplete"
  )
  if ($result.status -notin @("PASS_PREFIX", "PASS")) {
    throw "FAIL CLOSED: private matrix prefix verification failed."
  }
  $actual = @(Get-ProbeEvents)
  if ($actual.Count -gt $FrozenEvents.Count) {
    throw "FAIL CLOSED: private matrix has more than the eight frozen records."
  }
  for ($index = 0; $index -lt $actual.Count; $index++) {
    if ($actual[$index] -ne $FrozenEvents[$index]) {
      throw "FAIL CLOSED: private matrix is not the exact frozen R31 prefix."
    }
  }
  return $actual
}

function Invoke-OfflinePreflight {
  & py -3.12 -m pip install --require-hashes -r (Join-Path $PSScriptRoot "requirements-win-py312.txt")
  if ($LASTEXITCODE -ne 0) { throw "FAIL CLOSED: hash-pinned dependency installation failed." }
  & py -3.12 -m unittest -v `
    phase0.validation.exposure_preflight.test_exposure_preflight `
    phase0.validation.vps_reliability.test_reliability_oracle `
    phase0.validation.vps_reliability.test_private_probe `
    phase0.validation.vps_reliability.test_fault_drill_orchestrator
  if ($LASTEXITCODE -ne 0) { throw "FAIL CLOSED: G0-07 offline tests failed." }
}

function Capture-Exposure {
  param([Parameter(Mandatory=$true)][ValidateSet("PRE_DRILL", "POST_RECOVERY")][string]$Phase)
  $result = Invoke-PythonJson -Arguments @(
    (Join-Path $Repo "phase0\validation\exposure_preflight\exposure_preflight.py"),
    "--output", $Private, "--phase", $Phase
  )
  if ($result.status -ne "PASS_NO_OPEN_EXPOSURE" -or
      $result.positions_count -ne 0 -or $result.pending_orders_count -ne 0) {
    throw "FAIL CLOSED: zero-exposure check failed."
  }
  return $result
}

function Wait-ReadOnlyState {
  param(
    [Parameter(Mandatory=$true)][ValidateSet("HEALTHY", "DISCONNECTED")][string]$Expected,
    [int]$TimeoutSeconds = 180
  )
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    $lines = @(& py -3.12 (Join-Path $PSScriptRoot "fault_drill_state.py") --expected $Expected 2>&1 |
      ForEach-Object { $_.ToString() })
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) { return ($lines[-1] | ConvertFrom-Json -ErrorAction Stop) }
    if ($exitCode -eq 2) {
      throw "FAIL CLOSED: read-only state/barrier check failed. $($lines -join ' ')"
    }
    if ($exitCode -ne 3) { throw "FAIL CLOSED: unexpected state-check exit code $exitCode." }
    Start-Sleep -Seconds 3
  } while ((Get-Date) -lt $deadline)
  throw "FAIL CLOSED: $Expected recovery was not observed within $TimeoutSeconds seconds."
}

function Get-SingleTerminalProcess {
  $processes = @(Get-Process -Name terminal64 -ErrorAction SilentlyContinue)
  if ($processes.Count -ne 1) {
    throw "FAIL CLOSED: exactly one MT5 terminal64 process is required; observed $($processes.Count)."
  }
  if (-not $processes[0].Path) { throw "FAIL CLOSED: MT5 executable path is unavailable." }
  return $processes[0]
}

function Capture-Event {
  param([Parameter(Mandatory=$true)][string]$Event)
  if ($Event -notin $FrozenEvents[1..7]) { throw "FAIL CLOSED: event is outside frozen R31 scope." }
  $terminal = Get-SingleTerminalProcess
  $clock = Join-Path $Private ("w32tm-" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssfffZ") + ".txt")
  & w32tm.exe /query /status /verbose | Out-File -LiteralPath $clock -Encoding UTF8
  if ($LASTEXITCODE -ne 0) { throw "FAIL CLOSED: Windows Time status capture failed." }
  $boot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString("o")
  $mt5Start = $terminal.StartTime.ToUniversalTime().ToString("o")
  $arguments = @(
    (Join-Path $PSScriptRoot "private_probe.py"), "--output", $Private,
    "--event", $Event, "--scenario-id", $ScenarioIds[$Event],
    "--os-boot-utc", $boot, "--mt5-start-utc", $mt5Start,
    "--w32tm-status-file", $clock
  )
  if ($Event -eq "BUILD_CHECK" -and $CompatibilitySha256) {
    $arguments += @("--compatibility-sha256", $CompatibilitySha256)
  }
  $captured = Invoke-PythonJson -Arguments $arguments
  if ($captured.event -ne $Event -or $captured.tradeapi_disabled -ne $true) {
    throw "FAIL CLOSED: event capture or external-Python barrier assertion failed."
  }
  $null = Assert-ExactPrefix
  Save-Checkpoint -State ("CAPTURED_" + $Event) -Values @{
    last_event = $Event
    last_record_sha256 = $captured.record_sha256
  }
  return $captured
}

function Get-NetworkInterfaceIndex {
  $routes = @(Get-NetRoute -AddressFamily IPv4 -DestinationPrefix "0.0.0.0/0" -ErrorAction Stop |
    Where-Object { $_.State -eq "Alive" })
  if (-not $routes) { throw "FAIL CLOSED: no active IPv4 default route was found." }
  $ranked = foreach ($route in $routes) {
    $interface = Get-NetIPInterface -AddressFamily IPv4 -InterfaceIndex $route.InterfaceIndex -ErrorAction Stop
    [pscustomobject]@{
      InterfaceIndex = [int]$route.InterfaceIndex
      Rank = [int]$route.RouteMetric + [int]$interface.InterfaceMetric
    }
  }
  $bestRank = ($ranked | Measure-Object -Property Rank -Minimum).Minimum
  $best = @($ranked | Where-Object { $_.Rank -eq $bestRank } |
    Select-Object -ExpandProperty InterfaceIndex -Unique)
  if ($best.Count -ne 1) { throw "FAIL CLOSED: active default network path is ambiguous." }
  $adapter = Get-NetAdapter -InterfaceIndex $best[0] -ErrorAction Stop
  if ($adapter.Status -ne "Up") { throw "FAIL CLOSED: selected default network adapter is not up." }
  return [int]$best[0]
}

function Register-NetworkWatchdog {
  param([Parameter(Mandatory=$true)][int]$InterfaceIndex)
  if (Get-ScheduledTask -TaskName $NetworkWatchdogTaskName -ErrorAction SilentlyContinue) {
    throw "FAIL CLOSED: the reserved network recovery watchdog task already exists."
  }
  $command = "Get-NetAdapter -InterfaceIndex $InterfaceIndex -ErrorAction Stop | Enable-NetAdapter -Confirm:`$false"
  $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
  $action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
    -Argument "-NoProfile -NonInteractive -EncodedCommand $encoded"
  $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(3)
  $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
  Register-ScheduledTask -TaskName $NetworkWatchdogTaskName -Action $action -Trigger $trigger `
    -Principal $principal -Description "Bounded G0-07 R31 network recovery watchdog" | Out-Null
}

function Restore-NetworkAndRemoveWatchdog {
  param([Parameter(Mandatory=$true)][int]$InterfaceIndex)
  Get-NetAdapter -InterfaceIndex $InterfaceIndex -ErrorAction Stop | Enable-NetAdapter -Confirm:$false
  $deadline = (Get-Date).AddSeconds(60)
  do {
    $adapter = Get-NetAdapter -InterfaceIndex $InterfaceIndex -ErrorAction Stop
    if ($adapter.Status -eq "Up") { break }
    Start-Sleep -Seconds 2
  } while ((Get-Date) -lt $deadline)
  if ($adapter.Status -ne "Up") { throw "FAIL CLOSED: network adapter did not return to Up state." }
  if (Get-ScheduledTask -TaskName $NetworkWatchdogTaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $NetworkWatchdogTaskName -Confirm:$false
  }
}

function Register-InteractiveResume {
  param(
    [Parameter(Mandatory=$true)][string]$PreRestartBootUtc,
    [Parameter(Mandatory=$true)][string]$TerminalPath
  )
  if (Get-ScheduledTask -TaskName $ResumeTaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $ResumeTaskName -Confirm:$false
  }
  $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`" -Output `"$Private`" -ResumeAfterWindowsRestart"
  if ($CompatibilitySha256) { $arguments += " -CompatibilitySha256 $CompatibilitySha256" }
  $action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument $arguments
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity.Name
  $principal = New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType Interactive -RunLevel Highest
  Register-ScheduledTask -TaskName $ResumeTaskName -Action $action -Trigger $trigger -Principal $principal `
    -Description "Resume the bounded G0-07 R31 sequence after the approved Windows restart" | Out-Null
  Save-Checkpoint -State "AWAITING_WINDOWS_RESTART" -Values @{
    pre_restart_boot_utc = $PreRestartBootUtc
    terminal_path = $TerminalPath
    resume_user = $identity.Name
  }
}

function Assert-WindowsRestartOccurred {
  $checkpoint = Read-Checkpoint
  if ($null -eq $checkpoint -or $checkpoint.state -ne "AWAITING_WINDOWS_RESTART") {
    throw "FAIL CLOSED: Windows-restart checkpoint is missing or invalid."
  }
  if ($checkpoint.repository_head -ne (& git rev-parse HEAD).Trim()) {
    throw "FAIL CLOSED: repository revision changed across Windows restart."
  }
  $currentBoot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString("o")
  if ($currentBoot -eq $checkpoint.pre_restart_boot_utc) {
    throw "FAIL CLOSED: Windows boot timestamp did not change."
  }
}

function Complete-Drill {
  $matrix = Invoke-PythonJson -Arguments @(
    (Join-Path $PSScriptRoot "verify_private_matrix.py"), "--output", $Private
  )
  if ($matrix.status -ne "PASS") { throw "FAIL CLOSED: final private matrix did not pass." }
  $post = Capture-Exposure -Phase "POST_RECOVERY"
  $reconciliation = Invoke-PythonJson -Arguments @(
    (Join-Path $Repo "phase0\validation\exposure_preflight\exposure_preflight.py"),
    "--output", $Private, "--verify-reconciliation"
  )
  if ($reconciliation.status -ne "PASS_RECONCILED" -or
      $reconciliation.post_record_sha256 -ne $post.record_sha256) {
    throw "FAIL CLOSED: pre/post exposure reconciliation failed."
  }
  $preHash = $reconciliation.pre_record_sha256
  $safe = [ordered]@{
    schema = "gate0-vps-fault-publication-safe-summary-1.0"
    status = "PASS"
    completed_utc = (Get-Date).ToUniversalTime().ToString("o")
    frozen_events = $FrozenEvents
    final_matrix_record_sha256 = $matrix.final_record_sha256
    pre_exposure_record_sha256 = $preHash
    post_exposure_record_sha256 = $post.record_sha256
    positions_before = 0
    pending_orders_before = 0
    positions_after = 0
    pending_orders_after = 0
    external_python_trading = "DISABLED"
    claim_limit = "Controlled Gate 0 fault-drill evidence only; no trading authorization."
  }
  $safeJson = $safe | ConvertTo-Json -Depth 8 -Compress
  $hasher = [Security.Cryptography.SHA256]::Create()
  try {
    $safeHash = ([BitConverter]::ToString(
      $hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($safeJson))
    )).Replace("-", "").ToLowerInvariant()
  } finally {
    $hasher.Dispose()
  }
  $safe["summary_sha256"] = $safeHash
  $safe | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SafeSummaryPath -Encoding UTF8
  Save-Checkpoint -State "PASS" -Values @{
    pre_exposure_record_sha256 = $preHash
    post_exposure_record_sha256 = $post.record_sha256
    final_matrix_record_sha256 = $matrix.final_record_sha256
    publication_safe_summary_sha256 = $safeHash
  }
  if (Get-ScheduledTask -TaskName $ResumeTaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $ResumeTaskName -Confirm:$false
  }
  Write-Host ($safe | ConvertTo-Json -Depth 8 -Compress)
}

$mutex = [Threading.Mutex]::new($false, "Global\XAUUSD-G0-07-R31-Orchestrator")
if (-not $mutex.WaitOne(0)) { throw "FAIL CLOSED: another G0-07 orchestrator instance is active." }
try {
  Assert-Administrator
  [System.IO.Directory]::CreateDirectory($Private) | Out-Null
  Set-Location -LiteralPath $Repo
  $events = @(Assert-ExactPrefix)
  if ($events.Count -eq $FrozenEvents.Count) {
    $completed = Read-Checkpoint
    if ($null -ne $completed -and $completed.state -eq "PASS" -and
        (Test-Path -LiteralPath $SafeSummaryPath -PathType Leaf)) {
      Write-Host (Get-Content -LiteralPath $SafeSummaryPath -Raw)
      return
    }
    throw "FAIL CLOSED: complete matrix exists without a sealed PASS checkpoint; no evidence was appended."
  }

  if (-not $ResumeAfterWindowsRestart -and $events.Count -eq 1) {
    & git pull --ff-only origin main
    if ($LASTEXITCODE -ne 0) { throw "FAIL CLOSED: authoritative main fast-forward failed." }
    $localHead = (& git rev-parse HEAD).Trim()
    $remoteHead = (& git rev-parse origin/main).Trim()
    if ($LASTEXITCODE -ne 0 -or $localHead -ne $remoteHead) {
      throw "FAIL CLOSED: checkout is not the authoritative main revision."
    }
    Invoke-OfflinePreflight
    $pre = Capture-Exposure -Phase "PRE_DRILL"
    Save-Checkpoint -State "PRE_DRILL_PASS" -Values @{
      pre_exposure_record_sha256 = $pre.record_sha256
    }
  }
  $checkpoint = Read-Checkpoint
  if ($null -eq $checkpoint -or
      -not ($checkpoint.PSObject.Properties.Name -contains "pre_exposure_record_sha256")) {
    throw "FAIL CLOSED: successful pre-drill zero-exposure checkpoint is required."
  }

  $events = @(Assert-ExactPrefix)
  if ($events.Count -eq 1) {
    $interfaceIndex = Get-NetworkInterfaceIndex
    Register-NetworkWatchdog -InterfaceIndex $interfaceIndex
    try {
      Get-NetAdapter -InterfaceIndex $interfaceIndex -ErrorAction Stop | Disable-NetAdapter -Confirm:$false
      $null = Wait-ReadOnlyState -Expected "DISCONNECTED" -TimeoutSeconds 60
      $null = Capture-Event -Event "DISCONNECT"
    } finally {
      Restore-NetworkAndRemoveWatchdog -InterfaceIndex $interfaceIndex
    }
  }

  $events = @(Assert-ExactPrefix)
  if ($events.Count -eq 2) {
    $null = Wait-ReadOnlyState -Expected "HEALTHY" -TimeoutSeconds 180
    $null = Capture-Event -Event "RECONNECT"
  }
  $events = @(Assert-ExactPrefix)
  if ($events.Count -eq 3) {
    $null = Wait-ReadOnlyState -Expected "HEALTHY" -TimeoutSeconds 60
    $null = Capture-Event -Event "PYTHON_RESTART"
  }
  $events = @(Assert-ExactPrefix)
  if ($events.Count -eq 4) {
    $terminal = Get-SingleTerminalProcess
    $terminalPath = $terminal.Path
    if (-not $terminal.CloseMainWindow()) { throw "FAIL CLOSED: MT5 did not accept a graceful close request." }
    $terminal.WaitForExit(30 * 1000) | Out-Null
    if (-not $terminal.HasExited) { throw "FAIL CLOSED: MT5 did not close gracefully; no forced termination was used." }
    Start-Process -FilePath $terminalPath
    $null = Wait-ReadOnlyState -Expected "HEALTHY" -TimeoutSeconds 180
    $null = Capture-Event -Event "MT5_RESTART"
  }

  $events = @(Assert-ExactPrefix)
  if ($events.Count -eq 5) {
    $checkpoint = Read-Checkpoint
    $currentBoot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString("o")
    if ($null -ne $checkpoint -and $checkpoint.state -eq "AWAITING_WINDOWS_RESTART" -and
        $currentBoot -ne $checkpoint.pre_restart_boot_utc) {
      Assert-WindowsRestartOccurred
    } else {
      $terminal = Get-SingleTerminalProcess
      Register-InteractiveResume -PreRestartBootUtc $currentBoot -TerminalPath $terminal.Path
      Restart-Computer -Force
      return
    }
    $null = Wait-ReadOnlyState -Expected "HEALTHY" -TimeoutSeconds 240
    $null = Capture-Event -Event "WINDOWS_RESTART"
  }

  $events = @(Assert-ExactPrefix)
  if ($events.Count -eq 6) {
    $null = Wait-ReadOnlyState -Expected "HEALTHY" -TimeoutSeconds 60
    $null = Capture-Event -Event "CLOCK_CHECK"
  }
  $events = @(Assert-ExactPrefix)
  if ($events.Count -eq 7) {
    $healthy = Wait-ReadOnlyState -Expected "HEALTHY" -TimeoutSeconds 60
    $baseline = (Get-Content -LiteralPath $ProbeChainPath -First 1 | ConvertFrom-Json -ErrorAction Stop)
    if ($healthy.terminal_build -ne $baseline.terminal_build -and -not $CompatibilitySha256) {
      throw "FAIL CLOSED: terminal build changed and no verified compatibility artifact digest was supplied."
    }
    $null = Capture-Event -Event "BUILD_CHECK"
  }
  Complete-Drill
} catch {
  try { Save-Checkpoint -State "FAIL_CLOSED" -Values @{ reason = $_.Exception.Message } } catch { }
  Write-Error $_
  exit 2
} finally {
  $mutex.ReleaseMutex()
  $mutex.Dispose()
}
