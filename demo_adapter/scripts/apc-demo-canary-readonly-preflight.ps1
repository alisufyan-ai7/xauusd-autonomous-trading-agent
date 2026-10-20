# APC DEMO consolidated read-only preflight: OWNER APPROVAL REQUIRED before VPS use.
# Python source arrives as in-memory text and must match an externally pinned
# SHA-256. Python is piped via stdin (-B -I -): no -c quoting or source files.
# This wrapper performs NO Git, MT5 config, scheduler or order actions.
[CmdletBinding()]
param(
    [string] $PythonSource = '',
    [string] $ExpectedPythonSHA256 = '',
    [switch] $OwnerApprovedReadOnlyMT5,
    [switch] $ShellOnlyTest
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$pythonExe = 'C:\Program Files\Python312\python.exe'
$terminalExe = 'C:\Program Files\MetaTrader 5\terminal64.exe'

if ($ShellOnlyTest) {
    Write-Output 'APC_DEMO_PREFLIGHT_SHELL_ONLY_NO_PYTHON_NO_MT5'
    return
}
if (-not $OwnerApprovedReadOnlyMT5) {
    throw 'APC_DEMO_READONLY_MT5_PREFLIGHT_REQUIRES_NEW_OWNER_APPROVAL'
}
if (-not [IO.File]::Exists($pythonExe)) {
    throw 'APC_DEMO_PINNED_PYTHON_MISSING'
}
if ($ExpectedPythonSHA256 -cnotmatch '^[0-9a-f]{64}$') {
    throw 'APC_DEMO_INVALID_SOURCE_SHA_PIN'
}
$bytes = [Text.Encoding]::UTF8.GetBytes(
    $PythonSource.TrimEnd([char[]]@([char]13, [char]10)) + "`n"
)
$sha = [Security.Cryptography.SHA256]::Create()
try {
    $actual = [BitConverter]::ToString(
        $sha.ComputeHash($bytes)
    ).Replace('-', '').ToLowerInvariant()
}
finally { $sha.Dispose() }
if ($actual -cne $ExpectedPythonSHA256) {
    throw 'APC_DEMO_PREFLIGHT_PYTHON_SOURCE_MISMATCH_NOT_RUN'
}
function Inspect-Terminal {
    $items = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue)
    if ($items.Count -ne 1) { throw 'APC_DEMO_TERMINAL_SINGLETON_MISMATCH' }
    $item = $items[0]
    if ([string]::IsNullOrWhiteSpace($item.Path) -or
        -not [string]::Equals($item.Path, $terminalExe,
                             [StringComparison]::OrdinalIgnoreCase)) {
        throw 'APC_DEMO_TERMINAL_PATH_MISMATCH'
    }
    return [int]$item.Id
}
$beforeId = Inspect-Terminal
Write-Output ('APC_DEMO_PREATTACH_TERMINAL_PID=' + $beforeId)
$pythonError = $null
try {
    # PowerShell 5.1 sends an ASCII Python source stream; no -c double quotes.
    $pythonText = [Text.Encoding]::ASCII.GetString($bytes)
    if ($PythonSource -cne $pythonText.TrimEnd([char[]]@([char]13, [char]10))) {
        throw 'APC_DEMO_PREFLIGHT_REQUIRES_ASCII_SOURCE'
    }
    $pythonText | & $pythonExe -B -I - 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ('APC_DEMO_PREFLIGHT_PYTHON_FAILED_EXIT=' + $LASTEXITCODE)
    }
}
catch {
    $pythonError = $_
}
$afterId = Inspect-Terminal
if ($afterId -ne $beforeId) {
    throw 'APC_DEMO_MT5_TERMINAL_PROCESS_CHANGED_FAIL_CLOSED'
}
if ($null -ne $pythonError) { throw $pythonError }
Write-Output 'APC_DEMO_PREFLIGHT_COMPLETE_NO_ORDERS_NO_STAGING'
