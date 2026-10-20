#requires -Version 5.1
# PROSPECTIVE R2 DESIGN ONLY. Requires NEW, explicit exact-head owner approval.
# Never retry/overwrite the D0-R1 bootstrap failure or reuse its registration.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ExpectedCommit,
    [Parameter(Mandatory=$true)][string]$NewRegistrationSHA256,
    [Parameter(Mandatory=$true)][string]$WrapperSHA256,
    [Parameter(Mandatory=$true)][string]$PythonHostSHA256,
    [Parameter(Mandatory=$true)][string]$JournalSHA256,
    [switch]$ShellOnlyTest,
    [switch]$OwnerApprovedR2
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Pinned([string]$Path,[string]$Digest,[string]$Label) {
    if ($Digest -cnotmatch '^[0-9a-f]{64}$' -or -not [IO.File]::Exists($Path)) {
        throw "$Label FILE_OR_SHA_MISSING"
    }
    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -cne $Digest) { throw "$Label SHA256_MISMATCH" }
}
function Record-Stage([string]$Directory,[string]$Status) {
    $existing = @(Get-ChildItem -LiteralPath $Directory -Filter 'proof-*.json' -File)
    $filename = Join-Path $Directory ('proof-{0:D2}.json' -f ($existing.Count+1))
    $obj = [ordered]@{
        utc = [DateTime]::UtcNow.ToString('o')
        state = $Status
        registration_sha256 = $NewRegistrationSHA256
        intended_head = $ExpectedCommit
        market_data_admitted = $false
        trade_authority = $false
    }
    $bytes = [Text.Encoding]::UTF8.GetBytes(($obj | ConvertTo-Json -Compress) + [Environment]::NewLine)
    $stream = [IO.FileStream]::new(
        $filename,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None
    )
    try { $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true) }
    finally { $stream.Dispose() }
    Write-Output ('R2_PREFLIGHT_SHA256='+
        (Get-FileHash -LiteralPath $filename -Algorithm SHA256).Hash.ToLowerInvariant())
}
if ($ExpectedCommit -cnotmatch '^[0-9a-f]{40}$') { throw 'BAD_GITHUB_HEAD' }
foreach ($digest in @($NewRegistrationSHA256,$WrapperSHA256,$PythonHostSHA256,$JournalSHA256)) {
    if ($digest -cnotmatch '^[0-9a-f]{64}$') { throw 'BAD_REVIEWED_SHA256' }
}
if ($ShellOnlyTest) {
    Write-Output 'R2_SHELL_PREFLIGHT_PASS_NO_GIT_NO_MT5_NO_EVIDENCE_WRITES'
    return
}
if (-not $OwnerApprovedR2) { throw 'NEW_R2_OWNER_APPROVAL_REQUIRED' }
if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) { throw 'LOCALAPPDATA_MISSING' }
$stageDir = Join-Path $env:LOCALAPPDATA ('XAUUSD-v12-D0-R2-IsolatedStage\' + $NewRegistrationSHA256)
$privateDir = Join-Path $env:LOCALAPPDATA ('XAUUSD-v12-D0-PrivateEvidence\' + $NewRegistrationSHA256)
$rawFile = Join-Path $privateDir ('v12-d0-inventory-'+$NewRegistrationSHA256+'.json')
$journalFile = Join-Path $privateDir ('v12-attempt-'+$NewRegistrationSHA256+'.jsonl')
if ([IO.Directory]::Exists($stageDir) -or [IO.Directory]::Exists($privateDir)) {
    throw 'EXISTING_R2_ATTEMPT_DO_NOT_RERUN'
}
$null = [IO.Directory]::CreateDirectory($stageDir)
$priorGitPrompt = $env:GIT_TERMINAL_PROMPT
try {
    Record-Stage $stageDir 'RESERVED_R2_UNIQUE_ATTEMPT'
    $gitExe = (Get-Command git.exe -ErrorAction Stop).Source
    $env:GIT_TERMINAL_PROMPT = '0'
    & $gitExe init -q -- $stageDir
    if ($LASTEXITCODE -ne 0) { throw 'ISOLATED_GIT_INIT_FAILED' }
    & $gitExe -C $stageDir config core.autocrlf false
    if ($LASTEXITCODE -ne 0) { throw 'ISOLATED_GIT_CONFIG_FAILED' }
    & $gitExe -C $stageDir config core.eol lf
    if ($LASTEXITCODE -ne 0) { throw 'ISOLATED_GIT_EOL_FAILED' }
    & $gitExe -C $stageDir remote add origin 'https://github.com/alisufyan-ai7/xauusd-autonomous-trading-agent.git'
    if ($LASTEXITCODE -ne 0) { throw 'ISOLATED_GIT_REMOTE_FAILED' }
    & $gitExe -C $stageDir fetch --quiet --no-tags --depth=1 origin 'refs/pull/19/head'
    if ($LASTEXITCODE -ne 0) { throw 'ISOLATED_FETCH_FAILED' }
    $fetched = (& $gitExe -C $stageDir rev-parse FETCH_HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $fetched -cne $ExpectedCommit) {
        throw 'PR_HEAD_NOT_EXACTLY_APPROVED'
    }
    # Exact four approved functional files; no main worktree checkout/merge.
    $paths = @(
        'demo_adapter/scripts/v12-d0-readonly-inventory.ps1',
        'demo_adapter/scripts/v12_d0_readonly_inventory.py',
        'demo_adapter/scripts/v12_attempt_journal.py',
        'phase0/roadmap/DEMO_V12_D0_R2_FROZEN_REGISTRATION_2026-10-20.json'
    )
    & $gitExe -C $stageDir checkout FETCH_HEAD -- $paths
    if ($LASTEXITCODE -ne 0) { throw 'PINNED_CHECKOUT_FAILED' }
    $sourceRoot = Join-Path $stageDir 'demo_adapter'
    $psWrapperFile = Join-Path $sourceRoot 'scripts\v12-d0-readonly-inventory.ps1'
    $pythonHostFile = Join-Path $sourceRoot 'scripts\v12_d0_readonly_inventory.py'
    $journalSourceFile = Join-Path $sourceRoot 'scripts\v12_attempt_journal.py'
    $registrationFile = Join-Path $stageDir 'phase0\roadmap\DEMO_V12_D0_R2_FROZEN_REGISTRATION_2026-10-20.json'
    Assert-Pinned $psWrapperFile $WrapperSHA256 'WRAPPER'
    Assert-Pinned $pythonHostFile $PythonHostSHA256 'PYTHON_HOST'
    Assert-Pinned $journalSourceFile $JournalSHA256 'JOURNAL'
    Assert-Pinned $registrationFile $NewRegistrationSHA256 'R2_REGISTRATION'
    Record-Stage $stageDir 'EXACT_HEAD_AND_SOURCE_BYTE_PINS_PASSED'
    Write-Output ('VERIFIED_GITHUB_HEAD='+$fetched)

    # Pre-existing local Python only. Probe uses find_spec, NOT MetaTrader5 import.
    $possiblePython = [System.Collections.Generic.List[string]]::new()
    $locations = @(
        (Join-Path (Get-Location).Path '.venv\Scripts\python.exe'),
        (Join-Path $env:USERPROFILE 'Desktop\xauusd-autonomous-trading-agent\.venv\Scripts\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        'C:\Python312\python.exe'
    )
    foreach ($candidate in $locations) {
        if ([IO.File]::Exists($candidate) -and -not $possiblePython.Contains($candidate)) {
            $possiblePython.Add($candidate)
        }
    }
    $installedPython = Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $installedPython -and $installedPython.Source -notlike '*\WindowsApps\*' -and
        [IO.File]::Exists($installedPython.Source) -and -not $possiblePython.Contains($installedPython.Source)) {
        $possiblePython.Add($installedPython.Source)
    }
    $pythonExe = $null
    foreach ($candidate in $possiblePython) {
        try {
            $check = @(& $candidate -B -c 'import sys,importlib.util;print("READY" if sys.version_info[:2]==(3,12) and importlib.util.find_spec("MetaTrader5") else "NO")' 2>&1)
            if ($LASTEXITCODE -eq 0 -and $check -contains 'READY') {
                $pythonExe = $candidate
                break
            }
        } catch { }
    }
    if ($null -eq $pythonExe) { throw 'NO_EXISTING_PYTHON312_WITH_MT5_PREATTACH_FAIL' }
    $terminals = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue)
    if ($terminals.Count -ne 1 -or [string]::IsNullOrWhiteSpace($terminals[0].Path)) {
        throw 'REQUIRE_ONE_EXISTING_TERMINAL64_PREATTACH_FAIL'
    }
    $terminalExe = [IO.Path]::GetFullPath($terminals[0].Path)
    $terminalProcessId = [int]$terminals[0].Id
    if ([IO.Path]::GetFileName($terminalExe).ToLowerInvariant() -cne 'terminal64.exe') {
        throw 'NONADMITTED_TERMINAL_PROCESS'
    }
    Write-Output ('PYTHON_EXISTING='+$pythonExe)
    Write-Output ('TERMINAL_EXISTING='+$terminalExe)
    Write-Output ('TERMINAL_PID='+$terminalProcessId)
    Record-Stage $stageDir 'ONE_EXISTING_TERMINAL_AND_PYTHON_CONFIRMED'

    $arguments = @{
        IsolatedSourceRoot = $sourceRoot
        ExistingPythonExe = $pythonExe
        RegistrationFile = $registrationFile
        RegistrationSHA256 = $NewRegistrationSHA256
        PowerShellSHA256 = $WrapperSHA256
        HostSHA256 = $PythonHostSHA256
        JournalSHA256 = $JournalSHA256
        ApprovalPhrase = 'OWNER_APPROVED_EXACT_D0_INVENTORY_ONLY_NO_TRADING'
    }
    & $psWrapperFile @arguments
    if ($LASTEXITCODE -ne 0) { throw 'R2_REVIEWED_WRAPPER_FAILED' }
    $after = @(Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue)
    if ($after.Count -ne 1 -or [int]$after[0].Id -ne $terminalProcessId -or
        -not $after[0].Path.Equals($terminalExe,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'R2_TERMINAL_PROCESS_CHANGED_FAIL_CLOSED'
    }
    if (-not [IO.File]::Exists($rawFile) -or -not [IO.File]::Exists($journalFile)) {
        throw 'MISSING_PRIVATE_D0_R2_EVIDENCE'
    }
    Record-Stage $stageDir 'D0_R2_RAW_NOT_ADMITTED_TERMINAL_ID_UNCHANGED'
    Write-Output ('R2_RAW_SHA256='+(Get-FileHash -LiteralPath $rawFile -Algorithm SHA256).Hash.ToLowerInvariant())
    Write-Output ('R2_JOURNAL_SHA256='+(Get-FileHash -LiteralPath $journalFile -Algorithm SHA256).Hash.ToLowerInvariant())
    Write-Output 'D0_R2_RAW_ONLY_NOT_4H_NOT_TRADING'
} catch {
    try { Record-Stage $stageDir 'D0_R2_FAIL_CLOSED_NO_RERUN' } catch {}
    Write-Output ('R2_FAILURE_TYPE='+$_.Exception.GetType().Name)
    Write-Output 'R2_PRESERVE_ALL_EVIDENCE_DO_NOT_RERUN'
    if ([IO.File]::Exists($journalFile)) {
        Write-Output ('R2_PARTIAL_JOURNAL_SHA256='+
            (Get-FileHash -LiteralPath $journalFile -Algorithm SHA256).Hash.ToLowerInvariant())
    }
    throw
} finally {
    $env:GIT_TERMINAL_PROMPT = $priorGitPrompt
    Write-Output ('R2_STAGE_RETAINED='+$stageDir)
}
