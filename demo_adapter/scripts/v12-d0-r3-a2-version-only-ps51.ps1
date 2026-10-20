# Prospective D0-R3 A2: version-only, one NEW owner approval required.
# No MetaTrader5 import, MT5 attach, broker, orders, task changes or filesystem writes.
# This source must be pinned by SHA-256 and independently CI-tested before approval.
[CmdletBinding()]
param(
    [string] $OwnerApprovalCode = '',
    [switch] $ShellOnlyTest
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$pythonExecutable = 'C:\Program Files\Python312\python.exe'

if ($ShellOnlyTest) {
    Write-Output 'R3_A2_SHELL_ONLY_TEST__NO_PYTHON_OR_MT5'
    return
}
if ($OwnerApprovalCode -cne 'APPROVE_D0_R3_A2_VERSION_ONLY_ONCE') {
    throw 'R3_A2_NEW_OWNER_APPROVAL_REQUIRED__NOT_EXECUTED'
}
if (-not [IO.File]::Exists($pythonExecutable)) {
    throw 'R3_A2_PINNED_PYTHON_MISSING__FAIL_CLOSED'
}

# No inner quote characters: Windows PowerShell 5.1 passes this -c argument intact.
# -B disables bytecode writes; -I isolates user site and Python environment.
$code = 'import sys;print(sys.version_info[0],sys.version_info[1],sys.executable,sep=chr(124))'
$pythonOutput = @(& $pythonExecutable -B -I -c $code 2>&1)
$pythonExit = $LASTEXITCODE
if ($pythonExit -ne 0) {
    throw ('R3_A2_PYTHON_EXIT_NONZERO__FAIL_CLOSED__EXIT=' + $pythonExit)
}
if ($pythonOutput.Count -ne 1) {
    throw 'R3_A2_UNEXPECTED_OUTPUT_COUNT__FAIL_CLOSED'
}
$fields = ([string]$pythonOutput[0]).Split([char]'|')
if ($fields.Count -ne 3) {
    throw 'R3_A2_UNEXPECTED_OUTPUT_FIELDS__FAIL_CLOSED'
}
if ($fields[0] -cne '3' -or $fields[1] -cne '12') {
    throw 'R3_A2_WRONG_PYTHON_VERSION__FAIL_CLOSED'
}
if (-not [string]::Equals($fields[2], $pythonExecutable,
                        [StringComparison]::OrdinalIgnoreCase)) {
    throw 'R3_A2_PYTHON_EXECUTABLE_MISMATCH__FAIL_CLOSED'
}
Write-Output 'R3_A2_VERSION_ONLY_PASS__PYTHON=3.12'
Write-Output ('PYTHON_EXE=' + $fields[2])
Write-Output 'R3_A2_COMPLETE__NO_METATRADER5_IMPORT_OR_MT5_ATTACH'
