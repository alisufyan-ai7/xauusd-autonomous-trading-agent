# DEMO-ADMIT v1.1 - 4h attended read-only XAUUSD capture
# NOT AUTHORIZED until an EXACT prospective owner-approved run record exists.
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
if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    throw 'V11_LOCALAPPDATA_UNAVAILABLE'
}
$StageRoot = Join-Path $env:LOCALAPPDATA 'XAUUSD-DEMO-V11-READONLY'
$StageScripts = Join-Path $StageRoot 'scripts'
$StageMarker = Join-Path $StageRoot 'EXECUTION_OFF__NO_CAPTURE_AUTHORIZED'
if (-not [string]::Equals($PSScriptRoot, $StageScripts,
                         [StringComparison]::OrdinalIgnoreCase)) {
    throw 'V11_SCRIPT_OUTSIDE_ISOLATED_STAGE'
}
if (-not [string]::Equals((Split-Path -Parent $OutputDir), $StageRoot,
                         [StringComparison]::OrdinalIgnoreCase) -or
    (Split-Path -Leaf $OutputDir) -cnotmatch '^capture-[0-9]{8}T[0-9]{6}Z$' -or
    -not [IO.File]::Exists($StageMarker)) {
    throw 'V11_PRIVATE_OUTPUT_DIRECTORY_OR_STAGE_MISMATCH'
}
if (Test-Path -LiteralPath $OutputDir) {
    throw 'V11_OUTPUT_ALREADY_EXISTS__NO_RETRY'
}
$ActualRecordSHA = (Get-FileHash -LiteralPath $RunRecord -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualRecordSHA -cne $ExpectedRecordSHA256) {
    throw 'V11_RUN_RECORD_BYTE_SHA_MISMATCH'
}
# Require UTF-8 canonical JSON (sorted compact keys, one LF). Python confirms it.
$Registration = Get-Content -LiteralPath $RunRecord -Raw | ConvertFrom-Json
if ($Registration.approval_for_vps_capture -cne 'EXPLICIT_OWNER_APPROVED' -or
    $Registration.owner_approved_read_only_capture -ne $true -or
    $Registration.classification -cne 'DEMO_LIFECYCLE_ONLY_V1_1_READ_ONLY' -or
    $Registration.symbol -cne 'XAUUSD' -or
    $Registration.volume_max -cne '0.01' -or
    $Registration.mt5_external_python_trading_must_be_disabled -ne $true) {
    throw 'V11_NO_EXACT_OWNER_CAPTURE_APPROVAL'
}
$Python = 'C:\Program Files\Python312\python.exe'
$Terminal = 'C:\Program Files\MetaTrader 5\terminal64.exe'
$Collector = Join-Path $PSScriptRoot 'v11_windows_readonly_host.py'
$Primitive = Join-Path $PSScriptRoot 'v11_readonly_collector.py'
foreach ($Item in @($Python, $Collector, $Primitive)) {
    if (-not [IO.File]::Exists($Item)) {
        throw ('V11_REQUIRED_FILE_MISSING__' + $Item)
    }
}
$CollectorSHA = (Get-FileHash -LiteralPath $Collector -Algorithm SHA256).Hash.ToLowerInvariant()
$PrimitiveSHA = (Get-FileHash -LiteralPath $Primitive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($CollectorSHA -cne $Registration.exact_collector_source_sha256 -or
    $PrimitiveSHA -cne $Registration.exact_readonly_primitive_sha256) {
    throw 'V11_COLLECTOR_COMPONENT_SHA_MISMATCH'
}
if ($Registration.terminal_exe -cne $Terminal -or
    (($Registration.expected_terminal_pid -isnot [int]) -and
     ($Registration.expected_terminal_pid -isnot [long])) -or
    $Registration.expected_terminal_pid -le 0) {
    throw 'V11_UNAPPROVED_TERMINAL_IDENTITY'
}
function Assert-ExistingTerminal {
    $Processes = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue)
    if ($Processes.Count -ne 1) {
        throw 'V11_TERMINAL_COUNT_MISMATCH'
    }
    $Existing = $Processes[0]
    if ($Existing.Id -ne [int]$Registration.expected_terminal_pid -or
        -not [string]::Equals($Existing.Path, $Terminal,
                              [StringComparison]::OrdinalIgnoreCase)) {
        throw 'V11_TERMINAL_PID_OR_PATH_MISMATCH'
    }
}
Assert-ExistingTerminal
Write-Output 'V11_READONLY_CAPTURE_SOURCE_HASHES_VERIFIED'
Write-Output ('V11_RUN_RECORD_SHA256=' + $ActualRecordSHA)
Write-Output 'V11_READONLY_CAPTURE_ATTENDED_START_NO_ORDER_METHODS'
# -B -I, no task change, account login, order/check/margin/symbol-select API.
# MT5 initialize has possible side effects; requires separate owner approval.
& $Python -B -I $Collector --run-record $RunRecord --run-record-sha256 $ExpectedRecordSHA256 --output-dir $OutputDir
if ($LASTEXITCODE -ne 0) {
    throw ('V11_CAPTURE_FAILED_CLOSED__EXIT=' + $LASTEXITCODE)
}
Assert-ExistingTerminal
Write-Output 'V11_READONLY_CAPTURE_COMPLETED_NO_TRADING'
