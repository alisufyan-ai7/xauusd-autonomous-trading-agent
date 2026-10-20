# Prospectively review/approve BEFORE VPS use. Windows PowerShell 5.1 ONLY.
# Read-only four-hour DEMO XAUUSD capture, no trading enable or order API.
# This launcher deliberately refuses unapproved/unhashed run registrations.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string] $RunRecord,
    [Parameter(Mandatory=$true)][string] $ExpectedRecordSHA256,
    [Parameter(Mandatory=$true)][string] $OutputDir
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($PSVersionTable.PSVersion.Major -ne 5 -or
    $PSVersionTable.PSVersion.Minor -ne 1) {
    throw 'V11_WINDOWS_POWERSHELL_51_REQUIRED'
}
if ($ExpectedRecordSHA256 -cnotmatch '^[0-9a-f]{64}$') {
    throw 'V11_RUN_RECORD_SHA_PIN_MISSING'
}
if (-not [IO.Path]::IsPathRooted($RunRecord) -or
    -not [IO.File]::Exists($RunRecord) -or
    -not [IO.Path]::IsPathRooted($OutputDir)) {
    throw 'V11_PINNED_INPUT_OR_OUTPUT_PATH_INVALID'
}
$ExpectedStageRoot = Join-Path $env:LOCALAPPDATA 'XAUUSD-DEMO-V11-READONLY'
if ($PSScriptRoot -cne (Join-Path $ExpectedStageRoot 'scripts')) {
    throw 'V11_COLLECTOR_NOT_RUNNING_FROM_EXACT_ISOLATED_STAGE'
}
if ((Split-Path -Parent $OutputDir) -cne $ExpectedStageRoot -or
    (Split-Path -Leaf $OutputDir) -cnotmatch '^capture-[0-9]{8}T[0-9]{6}Z
$actualRecord = (Get-FileHash -LiteralPath $RunRecord -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualRecord -cne $ExpectedRecordSHA256) {
    throw 'V11_RUN_RECORD_BYTE_SHA_MISMATCH'
}
# Python checks canonical record SHA (sorted compact JSON) independently.
$registration = Get-Content -LiteralPath $RunRecord -Raw | ConvertFrom-Json
if ($registration.approval_for_vps_capture -cne 'EXPLICIT_OWNER_APPROVED' -or
    $registration.owner_approved_read_only_capture -ne $true -or
    $registration.classification -cne 'DEMO_LIFECYCLE_ONLY_V1_1_READ_ONLY' -or
    $registration.symbol -cne 'XAUUSD' -or
    $registration.volume_max -cne '0.01' -or
    $registration.mt5_external_python_trading_must_be_disabled -ne $true) {
    throw 'V11_NO_EXACT_OWNER_CAPTURE_APPROVAL'
}
$Python = 'C:\Program Files\Python312\python.exe'
$ExpectedTerminalExe = 'C:\Program Files\MetaTrader 5\terminal64.exe'
$Collector = Join-Path $PSScriptRoot 'v11_windows_readonly_host.py'
$Primitive = Join-Path $PSScriptRoot 'v11_readonly_collector.py'
if (-not [IO.File]::Exists($Python) -or
    -not [IO.File]::Exists($Collector) -or
    -not [IO.File]::Exists($Primitive)) {
    throw 'V11_EXISTING_RUNTIME_OR_SOURCE_MISSING'
}
$shaCollector = (Get-FileHash -LiteralPath $Collector -Algorithm SHA256).Hash.ToLowerInvariant()
$shaPrimitive = (Get-FileHash -LiteralPath $Primitive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($shaCollector -cne $registration.exact_collector_source_sha256 -or
    $shaPrimitive -cne $registration.exact_readonly_primitive_sha256) {
    throw 'V11_SOURCE_COMPONENT_SHA_MISMATCH'
}
if ($registration.terminal_exe -cne $ExpectedTerminalExe -or
    (($registration.expected_terminal_pid -isnot [int]) -and
     ($registration.expected_terminal_pid -isnot [long])) -or
    $registration.expected_terminal_pid -le 0) {
    throw 'V11_UNAPPROVED_TERMINAL_IDENTITY'
}
function Assert-SingleExistingTerminal {
    $processes = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue)
    if ($processes.Count -ne 1) {
        throw 'V11_TERMINAL_SINGLETON_MISMATCH'
    }
    $found = $processes[0]
    if ($found.Id -ne [int]$registration.expected_terminal_pid -or
        -not [string]::Equals($found.Path,$ExpectedTerminalExe,
                             [StringComparison]::OrdinalIgnoreCase)) {
        throw 'V11_TERMINAL_PID_OR_PATH_MISMATCH'
    }
}
Assert-SingleExistingTerminal
Write-Output 'V11_READONLY_CAPTURE_SOURCE_HASHES_VERIFIED'
Write-Output ('V11_RUN_RECORD_SHA256=' + $actualRecord)
Write-Output 'V11_READONLY_CAPTURE_ATTENDED_START_NO_ORDER_METHODS'
# No jobs/scheduler, no global config or MT5 trading setting toggles.
# Existing terminal attachment may have side effects; needs separate approval.
& $Python -B -I $Collector --run-record $RunRecord --run-record-sha256 $ExpectedRecordSHA256 --output-dir $OutputDir
if ($LASTEXITCODE -ne 0) {
    throw ('V11_CAPTURE_FAILED_CLOSED__EXIT=' + $LASTEXITCODE)
}
Assert-SingleExistingTerminal
Write-Output 'V11_READONLY_CAPTURE_COMPLETED_NO_TRADING'
 -or
    -not [IO.File]::Exists((Join-Path $ExpectedStageRoot 'EXECUTION_OFF__NO_CAPTURE_AUTHORIZED'))) {
    throw 'V11_PRIVATE_OUTPUT_DIRECTORY_OR_STAGE_MISMATCH'
}
if (Test-Path -LiteralPath $OutputDir) {
    throw 'V11_OUTPUT_ALREADY_EXISTS__NO_RETRY'
}
$actualRecord = (Get-FileHash -LiteralPath $RunRecord -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualRecord -cne $ExpectedRecordSHA256) {
    throw 'V11_RUN_RECORD_BYTE_SHA_MISMATCH'
}
# Python checks canonical record SHA (sorted compact JSON) independently.
$registration = Get-Content -LiteralPath $RunRecord -Raw | ConvertFrom-Json
if ($registration.approval_for_vps_capture -cne 'EXPLICIT_OWNER_APPROVED' -or
    $registration.owner_approved_read_only_capture -ne $true -or
    $registration.classification -cne 'DEMO_LIFECYCLE_ONLY_V1_1_READ_ONLY' -or
    $registration.symbol -cne 'XAUUSD' -or
    $registration.volume_max -cne '0.01' -or
    $registration.mt5_external_python_trading_must_be_disabled -ne $true) {
    throw 'V11_NO_EXACT_OWNER_CAPTURE_APPROVAL'
}
$Python = 'C:\Program Files\Python312\python.exe'
$ExpectedTerminalExe = 'C:\Program Files\MetaTrader 5\terminal64.exe'
$Collector = Join-Path $PSScriptRoot 'v11_windows_readonly_host.py'
$Primitive = Join-Path $PSScriptRoot 'v11_readonly_collector.py'
if (-not [IO.File]::Exists($Python) -or
    -not [IO.File]::Exists($Collector) -or
    -not [IO.File]::Exists($Primitive)) {
    throw 'V11_EXISTING_RUNTIME_OR_SOURCE_MISSING'
}
$shaCollector = (Get-FileHash -LiteralPath $Collector -Algorithm SHA256).Hash.ToLowerInvariant()
$shaPrimitive = (Get-FileHash -LiteralPath $Primitive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($shaCollector -cne $registration.exact_collector_source_sha256 -or
    $shaPrimitive -cne $registration.exact_readonly_primitive_sha256) {
    throw 'V11_SOURCE_COMPONENT_SHA_MISMATCH'
}
if ($registration.terminal_exe -cne $ExpectedTerminalExe -or
    (($registration.expected_terminal_pid -isnot [int]) -and
     ($registration.expected_terminal_pid -isnot [long])) -or
    $registration.expected_terminal_pid -le 0) {
    throw 'V11_UNAPPROVED_TERMINAL_IDENTITY'
}
function Assert-SingleExistingTerminal {
    $processes = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue)
    if ($processes.Count -ne 1) {
        throw 'V11_TERMINAL_SINGLETON_MISMATCH'
    }
    $found = $processes[0]
    if ($found.Id -ne [int]$registration.expected_terminal_pid -or
        -not [string]::Equals($found.Path,$ExpectedTerminalExe,
                             [StringComparison]::OrdinalIgnoreCase)) {
        throw 'V11_TERMINAL_PID_OR_PATH_MISMATCH'
    }
}
Assert-SingleExistingTerminal
Write-Output 'V11_READONLY_CAPTURE_SOURCE_HASHES_VERIFIED'
Write-Output ('V11_RUN_RECORD_SHA256=' + $actualRecord)
Write-Output 'V11_READONLY_CAPTURE_ATTENDED_START_NO_ORDER_METHODS'
# No jobs/scheduler, no global config or MT5 trading setting toggles.
# Existing terminal attachment may have side effects; needs separate approval.
& $Python -B -I $Collector --run-record $RunRecord --run-record-sha256 $ExpectedRecordSHA256 --output-dir $OutputDir
if ($LASTEXITCODE -ne 0) {
    throw ('V11_CAPTURE_FAILED_CLOSED__EXIT=' + $LASTEXITCODE)
}
Assert-SingleExistingTerminal
Write-Output 'V11_READONLY_CAPTURE_COMPLETED_NO_TRADING'
