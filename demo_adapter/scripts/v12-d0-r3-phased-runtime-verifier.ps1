# PROSPECTIVE D0-R3 — NEVER RUN WITHOUT NEW PHASE-SPECIFIC OWNER APPROVAL.
# No Git/network, disk writes, Task Scheduler or MT5 initialize/broker/order API.
# VERSION_ONLY launches exactly existing Python for sys.version check (no MT5 import).
# IMPORT_ONLY separately imports MetaTrader5 WITHOUT calling any MT5 method.
# TERMINAL_ONLY does not launch Python or MT5; only reads existing terminal process.
# ShellOnlyTest only exercises argument/guard logic; never starts Python/MT5.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('VERSION_ONLY','IMPORT_ONLY','TERMINAL_ONLY')]
    [string] $Phase,
    [string] $OwnerApprovalCode = '',
    [switch] $ShellOnlyTest
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$pythonExecutable = 'C:\Program Files\Python312\python.exe'
$terminalExecutable = 'C:\Program Files\MetaTrader 5\terminal64.exe'
$terminalProcessId = 6216

if ($ShellOnlyTest) {
    Write-Output ('R3_SHELL_ONLY_TEST__NO_PYTHON_MT5__PHASE=' + $Phase)
    return
}
$requiredOwnerCode = 'APPROVE_D0_R3_' + $Phase + '_ONCE'
if ($OwnerApprovalCode -cne $requiredOwnerCode) {
    throw ('R3_PHASE_SEPARATE_OWNER_APPROVAL_REQUIRED__' + $Phase)
}

if ($Phase -eq 'TERMINAL_ONLY') {
    $terminalProcesses = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue)
    if ($terminalProcesses.Count -ne 1) {
        throw 'R3_TERMINAL_COUNT_MISMATCH__FAIL_CLOSED'
    }
    $existingTerminal = $terminalProcesses[0]
    if ($existingTerminal.Id -ne $terminalProcessId) {
        throw 'R3_TERMINAL_PID_MISMATCH__FAIL_CLOSED'
    }
    try {
        $actualTerminalPath = $existingTerminal.Path
    }
    catch {
        throw 'R3_TERMINAL_PROCESS_PATH_UNAVAILABLE__FAIL_CLOSED'
    }
    if ([string]::IsNullOrWhiteSpace($actualTerminalPath)) {
        throw 'R3_TERMINAL_PROCESS_PATH_UNAVAILABLE__FAIL_CLOSED'
    }
    if (-not [string]::Equals($actualTerminalPath, $terminalExecutable,
                            [StringComparison]::OrdinalIgnoreCase)) {
        throw 'R3_TERMINAL_EXECUTABLE_MISMATCH__FAIL_CLOSED'
    }
    Write-Output ('R3_TERMINAL_ONLY_PASS__PID=' + $terminalProcessId)
    Write-Output ('TERMINAL_EXE=' + $actualTerminalPath)
    Write-Output 'NO_PYTHON_NO_MT5_IMPORT_NO_MT5_ATTACH'
    return
}
if (-not [IO.File]::Exists($pythonExecutable)) {
    throw 'R3_PINNED_PYTHON_EXECUTABLE_MISSING__FAIL_CLOSED'
}
if ($Phase -eq 'VERSION_ONLY') {
    # -B disables .pyc creation; -I isolates Python environment/path.
    $code = 'import sys,os; expected=r"C:\Program Files\Python312\python.exe"; assert sys.version_info[:2]==(3,12), "WRONG_VERSION"; assert os.path.normcase(os.path.abspath(sys.executable))==os.path.normcase(os.path.abspath(expected)), "WRONG_EXECUTABLE"; print("R3_VERSION_ONLY_PASS__PYTHON=3.12"); print("PYTHON_EXE="+sys.executable)'
}
elseif ($Phase -eq 'IMPORT_ONLY') {
    # No initialize(), no broker read, no MetaTrader5 API methods of any kind.
    $code = 'import sys,os,importlib.metadata as md; expected=r"C:\Program Files\Python312\python.exe"; assert sys.version_info[:2]==(3,12), "WRONG_VERSION"; assert os.path.normcase(os.path.abspath(sys.executable))==os.path.normcase(os.path.abspath(expected)), "WRONG_EXECUTABLE"; import MetaTrader5 as mt5; print("R3_IMPORT_ONLY_PASS__DIST_VERSION="+md.version("MetaTrader5")); print("MODULE_VERSION="+str(getattr(mt5,"__version__","UNREPORTED")))'
}
else {
    throw 'R3_UNKNOWN_PHASE__FAIL_CLOSED'
}
$pythonOutput = @(& $pythonExecutable -B -I -c $code 2>&1)
if ($LASTEXITCODE -ne 0) {
    throw ('R3_PYTHON_PREFLIGHT_FAILED__PHASE=' + $Phase + '__EXIT=' + $LASTEXITCODE)
}
foreach ($outputLine in $pythonOutput) {
    Write-Output ([string]$outputLine)
}
Write-Output ('R3_PHASE_COMPLETE_NO_MT5_ATTACH__' + $Phase)
