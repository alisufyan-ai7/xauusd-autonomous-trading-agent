#requires -Version 5.1
<#
 D0 DISCOVERY ONLY. Requires explicit OWNER approval of exact D0 SHA and exact
 host/journal/registration pins. NOT the frozen 240-minute v1.2 capture.
 NO TaskScheduler/MT5 settings/order APIs/broker operations or trading enablement.
 Requires exactly one ALREADY RUNNING terminal64.exe; initialize() may still
 launch/reactivate a terminal, therefore compare exact PID and path before/after,
 abort evidence qualification if it changes. Owner must accept attach risk.
 The only intended writes are newly created PRIVATE D0 evidence directory;
 no shared repo/worktree mutation.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$IsolatedSourceRoot,
    [Parameter(Mandatory=$true)][string]$ExistingPythonExe,
    [Parameter(Mandatory=$true)][string]$RegistrationFile,
    [Parameter(Mandatory=$true)][string]$RegistrationSHA256,
    [Parameter(Mandatory=$true)][string]$PowerShellSHA256,
    [Parameter(Mandatory=$true)][string]$HostSHA256,
    [Parameter(Mandatory=$true)][string]$JournalSHA256,
    [Parameter(Mandatory=$true)][string]$ApprovalPhrase
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-SHA([string]$path,[string]$expected,[string]$label) {
    if ($expected -cnotmatch '^[0-9a-f]{64}$') { throw "$label UNREGISTERED_SHA256" }
    if (-not [IO.File]::Exists($path)) { throw "$label FILE_NOT_PRESENT" }
    $real = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($real -cne $expected) { throw "$label BYTE_HASH_MISMATCH" }
}
if ($ApprovalPhrase -cne "OWNER_APPROVED_EXACT_D0_INVENTORY_ONLY_NO_TRADING") {
    throw "D0_APPROVAL_NOT_CONFIRMED"
}
$base = [IO.Path]::GetFullPath($IsolatedSourceRoot)
$python = [IO.Path]::GetFullPath($ExistingPythonExe)
$reg = [IO.Path]::GetFullPath($RegistrationFile)
$self = [IO.Path]::GetFullPath($MyInvocation.MyCommand.Path)
$hostSource = Join-Path $base "scripts\v12_d0_readonly_inventory.py"
$journalSource = Join-Path $base "scripts\v12_attempt_journal.py"
if (-not [IO.File]::Exists($python) -or
    -not [IO.Directory]::Exists((Join-Path $base "scripts"))) {
    throw "ISOLATED_SOURCE_OR_EXISTING_PYTHON_MISSING"
}
Assert-SHA $self $PowerShellSHA256 "D0_PS51_WRAPPER"
Assert-SHA $hostSource $HostSHA256 "D0_HOST"
Assert-SHA $journalSource $JournalSHA256 "D0_JOURNAL"
Assert-SHA $reg $RegistrationSHA256 "D0_REGISTRATION"
$contract = Get-Content -LiteralPath $reg -Raw -Encoding UTF8 | ConvertFrom-Json
if ($contract.mode -cne "D0_SOURCE_DISCOVERY_SINGLE_SNAPSHOT_ONLY" -or
    $contract.collector_ps_sha256 -cne $PowerShellSHA256 -or
    $contract.host_sha256 -cne $HostSHA256 -or
    $contract.attempt_journal_sha256 -cne $JournalSHA256 -or
    $contract.broker_trading_allowed -ne $false -or
    $contract.four_hour_capture_allowed -ne $false -or
    $contract.vps_mt5_execution_authorized_in_git -ne $false) {
    throw "D0_PROSPECTIVE_REGISTRATION_NOT_CONFORMING"
}
$all = @(Get-Process -Name "terminal64" -ErrorAction SilentlyContinue)
if ($all.Count -ne 1 -or [string]::IsNullOrEmpty($all[0].Path)) {
    throw "NEED_EXACT_ONE_PREEXISTING_TERMINAL_PROCESS_NO_NEW_TERMINAL_START"
}
$terminal = [IO.Path]::GetFullPath($all[0].Path)
if ([IO.Path]::GetFileName($terminal).ToLowerInvariant() -cne "terminal64.exe") {
    throw "EXACT_PREEXISTING_TERMINAL_EXE_NOT_VERIFIED"
}
$pidBefore = [int]$all[0].Id

# Only one private directory, fixed by SHA registration. No existing evidence
# is overwritten, merged, relabeled or retried. Same registration is one attempt.
$privateRoot = Join-Path $env:LOCALAPPDATA "XAUUSD-v12-D0-PrivateEvidence"
$privateDir = Join-Path $privateRoot $RegistrationSHA256
if ([IO.Directory]::Exists($privateDir)) {
    throw "D0_ATTEMPT_DIRECTORY_ALREADY_EXISTS_NO_RERUN"
}
if (-not [IO.Directory]::Exists($privateRoot)) {
    $null = [IO.Directory]::CreateDirectory($privateRoot)
}
# Remove inherited ACL; only current Windows user can read/write this new
# evidence directory. If Windows ACL application fails, abort before MT5 attach.
$null = [IO.Directory]::CreateDirectory($privateDir)
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true,$false)
    $rule = [Security.AccessControl.FileSystemAccessRule]::new(
        $identity.User,
        [Security.AccessControl.FileSystemRights]::FullControl,
        ([Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
         [Security.AccessControl.InheritanceFlags]::ObjectInherit),
        [Security.AccessControl.PropagationFlags]::None,
        [Security.AccessControl.AccessControlType]::Allow
    )
    $acl.AddAccessRule($rule)
    (Get-Item -LiteralPath $privateDir).SetAccessControl($acl)
} catch {
    throw "D0_PRIVATE_ACL_CANNOT_BE_ESTABLISHED_NO_MT5_ATTACH"
}
$oldDir = (Get-Location).Path
$priorBytecode = $env:PYTHONDONTWRITEBYTECODE
try {
    Set-Location $base
    $env:PYTHONDONTWRITEBYTECODE = "1"
    & $python -B -m scripts.v12_d0_readonly_inventory `
        --registration $reg `
        --registration-sha256 $RegistrationSHA256 `
        --host-sha256 $HostSHA256 `
        --attempt-journal-sha256 $JournalSHA256 `
        --terminal $terminal `
        --private-dir $privateDir `
        --owner-d0-confirmed
    if ($LASTEXITCODE -ne 0) {
        throw "D0_FAIL_CLOSED_NO_SOURCE_OR_FOUR_HOUR_ADMISSION"
    }
}
finally {
    Set-Location $oldDir
    $env:PYTHONDONTWRITEBYTECODE = $priorBytecode
    $after = @(Get-Process -Name "terminal64" -ErrorAction SilentlyContinue)
    if ($after.Count -ne 1 -or
        [int]$after[0].Id -ne $pidBefore -or
        -not $after[0].Path.Equals($terminal,[StringComparison]::OrdinalIgnoreCase)) {
        Write-Error "D0_TERMINAL_PROCESS_CHANGED__NOT_ADMITTED_CHECK_BY_HUMAN"
    }
}
Write-Output "D0_COMPLETED_PRIVATE_RAW_ONLY__V12_FOUR_HOUR_CAPTURE_NOT_AUTHORIZED"
