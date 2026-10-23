#requires -Version 5.1
# V2 PR33 ISOLATED PYTHON3.12 TEST RUNNER -- NO MT5 OR BROKER OPERATIONS.
# This source is PREPARED ONLY; it has NOT been run on the user's VPS.
$ErrorActionPreference = 'Stop'
$Repo = 'C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent'
$Branch = 'implementation/pro-v2-readonly-data-and-tpb-shadow-20261022'
$ExpectedSource = '4bfb431daf078c84d4189a4c033a2d607ae53004'
$Temp = Join-Path $env:TEMP ('xauusd-pro-v2-tests-' + [guid]::NewGuid().ToString('N'))
$Export = Join-Path $Temp 'source'
$Archive = Join-Path $Temp 'source.zip'
if (-not (Test-Path -LiteralPath (Join-Path $Repo '.git'))) {
    throw "Expected repository not found at $Repo. No changes made."
}
New-Item -ItemType Directory -Path $Export -Force | Out-Null

# Fetch source without changing the live worktree or installed Windows tasks.
& git -C $Repo fetch --no-tags origin "refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
$ObservedHead = (& git -C $Repo rev-parse FETCH_HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not resolve fetched branch' }
& git -C $Repo merge-base --is-ancestor $ExpectedSource $ObservedHead
if ($LASTEXITCODE -ne 0) {
    throw 'Frozen source is not an ancestor of fetched branch. Refuse testing a changed lineage.'
}
& git -C $Repo archive --format=zip "--output=$Archive" $ExpectedSource
if ($LASTEXITCODE -ne 0) { throw 'Could not archive exact source commit' }
Expand-Archive -LiteralPath $Archive -DestinationPath $Export -Force
Write-Output "V2_TEST_SOURCE_COMMIT=$ExpectedSource"
Write-Output "V2_REMOTE_HEAD=$ObservedHead"
Write-Output "V2_ISOLATED_SOURCE=$Export"

$Candidates = @((Join-Path $Repo '.venv\Scripts\python.exe'), 'C:\Program Files\Python312\python.exe')
$Python = $null
foreach ($Candidate in $Candidates) {
    if (-not (Test-Path -LiteralPath $Candidate)) { continue }
    $Version = (& $Candidate -c 'import sys; print(".".join(map(str,sys.version_info[:2])))' 2>$null)
    if ($LASTEXITCODE -eq 0 -and $Version.Trim() -eq '3.12') {
        $Python = $Candidate
        break
    }
}
if (-not $Python) { throw 'No Python3.12 interpreter found; no packages installed' }
Write-Output "V2_PY312_BIN=$Python"

Push-Location -LiteralPath $Export
try {
    & $Python -m compileall -q src tests/unit/features/test_v2_shadow_context.py tests/unit/broker/test_v2_mt5_extended_readonly.py tests/unit/features/test_v2_tpb_event_shadow.py tests/unit/ops/test_v2_demo_paper_lifecycle.py tests/unit/risk/test_v2_cash_preflight.py
    if ($LASTEXITCODE -ne 0) { throw 'V2_PY312_COMPILE_FAIL' }
    Write-Output 'V2_PY312_COMPILE_PASS'

    & $Python -m pytest --version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'pytest unavailable in selected Python3.12 interpreter; no installation attempted'
    }
    & $Python -m pytest -q tests/unit/features/test_v2_shadow_context.py tests/unit/broker/test_v2_mt5_extended_readonly.py tests/unit/features/test_v2_tpb_event_shadow.py tests/unit/ops/test_v2_demo_paper_lifecycle.py tests/unit/risk/test_v2_cash_preflight.py
    if ($LASTEXITCODE -ne 0) { throw 'V2_PY312_TEST_FAIL' }
    Write-Output 'V2_PY312_SELECTED_TESTS_PASS'

    & $Python scripts/verify_execution_disabled.py
    if ($LASTEXITCODE -ne 0) { throw 'V2_EXECUTION_DISABLED_CAPABILITY_SCAN_FAIL' }
    Write-Output 'V2_EXECUTION_DISABLED_CAPABILITY_SCAN_PASS'
}
finally {
    Pop-Location
}
Write-Output 'V2_NATIVE_TESTS_COMPLETE_NO_BROKER_ACTIONS'
