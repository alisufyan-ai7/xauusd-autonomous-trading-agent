# S2 future-only attended canary launcher; NO VPS execution / broker approval.
# This does not change MT5's external-Python trading toggle.
# Always verify this script + the frozen S2 archive and loader SHA externally.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('VERIFY','ENTRY','CLOSE')]
    [string] $Mode,
    [Parameter(Mandatory=$true)][string] $ExactHead,
    [Parameter(Mandatory=$true)][string] $ExactBundleSHA,
    [Parameter(Mandatory=$true)][string] $ExactLoaderSHA,
    [Parameter(Mandatory=$true)][int] $ExpectedTerminalPID,
    [string] $OwnerApproval = '',
    [string] $ActivationId = '',
    [string] $ExpiryUTC = '',
    [string] $Side = '',
    [string] $Stop = '',
    [switch] $ShellOnlyTest
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($ShellOnlyTest) {
    Write-Output 'S2_SHELL_ONLY_NO_PYTHON_NO_MT5'
    return
}
if ($ExactHead -cnotmatch '^[0-9a-f]{40}$' -or
    $ExactBundleSHA -cnotmatch '^[0-9a-f]{64}$' -or
    $ExactLoaderSHA -cnotmatch '^[0-9a-f]{64}$') {
    throw 'S2_INVALID_EXACT_SOURCE_HASH_PINS'
}
$python = 'C:\Program Files\Python312\python.exe'
$terminalExe = 'C:\Program Files\MetaTrader 5\terminal64.exe'
$stage = Join-Path $env:LOCALAPPDATA 'XAUUSD-APC-DEMO-CANARY-S2'
$loader = Join-Path $stage 'sources\apc_demo_canary_s2_isolated_loader.py'
if (-not [IO.File]::Exists($python) -or -not [IO.File]::Exists($loader)) {
    throw 'S2_PINNED_RUNTIME_OR_STAGE_NOT_PRESENT'
}
$actualLoaderSHA = (Get-FileHash -LiteralPath $loader -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualLoaderSHA -cne $ExactLoaderSHA) {
    throw 'S2_ISOLATED_LOADER_HASH_MISMATCH__NOT_EXECUTED'
}
$actualZipSHA = (Get-FileHash -LiteralPath (Join-Path $stage 'sealed.zip') -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualZipSHA -cne $ExactBundleSHA) {
    throw 'S2_SEALED_ARTIFACT_HASH_MISMATCH__NOT_EXECUTED'
}
function Assert-Terminal {
    $list = @(Get-Process -Name terminal64 -ErrorAction SilentlyContinue)
    if ($list.Count -ne 1) { throw 'S2_TERMINAL_SINGLETON_NOT_PROVEN' }
    $one = $list[0]
    if ($one.Id -ne $ExpectedTerminalPID -or
        -not [string]::Equals($one.Path, $terminalExe,
                             [StringComparison]::OrdinalIgnoreCase)) {
        throw 'S2_TERMINAL_IDENTITY_NOT_PROVEN'
    }
}
Assert-Terminal
$argsPy = @($loader, '--mode', $Mode.ToLowerInvariant(),
           '--expected-git-head', $ExactHead,
           '--expected-archive-sha256', $ExactBundleSHA)
if ($Mode -ne 'VERIFY') {
    if ($OwnerApproval -cne 'APC-DEMO-CANARY-ONE-ENTRY-ONE-CLOSE') {
        throw 'S2_SEPARATE_EXPLICIT_OWNER_BROKER_APPROVAL_REQUIRED'
    }
    if ([string]::IsNullOrWhiteSpace($ActivationId) -or
        [string]::IsNullOrWhiteSpace($ExpiryUTC)) {
        throw 'S2_OWNER_ACTIVATION_WINDOW_REQUIRED'
    }
    $argsPy += @('--owner-apc', $OwnerApproval,
                 '--activation-id', $ActivationId,
                 '--expires-utc', $ExpiryUTC)
    if ($Mode -eq 'ENTRY') {
        if ($Side -cnotin @('BUY','SELL') -or [string]::IsNullOrWhiteSpace($Stop)) {
            throw 'S2_OWNER_APPROVED_SIDE_AND_SL_REQUIRED'
        }
        $argsPy += @('--side', $Side, '--stop', $Stop)
    }
    elseif ($Side -ne '' -or $Stop -ne '') {
        throw 'S2_CLOSE_CANNOT_SPECIFY_NEW_RISK'
    }
}
# No retry; no automatic MT5 terminal toggling; no background process/task.
& $python -B -I @argsPy
if ($LASTEXITCODE -ne 0) {
    throw ('S2_ATTENDED_MODE_FAIL_CLOSED_' + $Mode)
}
Assert-Terminal
Write-Output ('S2_ATTENDED_MODE_FINISHED_' + $Mode)
Write-Output 'S2_NO_AUTOMATIC_RETRY_OR_TERMINAL_SETTING_CHANGE'
