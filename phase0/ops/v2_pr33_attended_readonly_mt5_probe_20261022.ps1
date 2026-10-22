#requires -Version 5.1
# PRO V2 EXTENDED DEMO DATA PROBE: READ ONLY, OWNER-ATTENDED ONLY.
# NOT a scheduled service. NO order APIs, login, account switch, settings edits.
# Requires an already-open project Exness Pro DEMO MT5 and external Python
# automated trading DISABLED in terminal settings. Never print raw account IDs.
$ErrorActionPreference = 'Stop'
$Repo = 'C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent'
$Branch = 'implementation/pro-v2-readonly-data-and-tpb-shadow-20261022'
$PinnedCode = '833abb905c11883d9154c5ad8e789fcfae5fb1f9'
$Python = 'C:\Program Files\Python312\python.exe'

if (-not (Test-Path -LiteralPath (Join-Path $Repo '.git'))) {
    throw 'No expected project Git repository; do not change working tree'
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw 'Python 3.12 missing; do not install automatically'
}
# Avoid Python quoted f-strings inside PowerShell 5.1 native argument parsing.
# Numeric version probe is quote-free and returns 312 for Python 3.12.x.
$pyver = (& $Python -c 'import sys;print(sys.version_info.major*100+sys.version_info.minor)')
if ($LASTEXITCODE -ne 0 -or $pyver.Trim() -ne '312') {
    throw 'Exact Python 3.12 required; no fallback allowed'
}
# Read-only market probe is imported from an immutable Git archive; no
# checkout/switch/reset/pull in the installed production working directory.
& git -C $Repo fetch --no-tags origin "refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'Could not fetch review branch' }
$observedHead = (& git -C $Repo rev-parse FETCH_HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot identify remote HEAD' }
& git -C $Repo merge-base --is-ancestor $PinnedCode $observedHead
if ($LASTEXITCODE -ne 0) {
    throw 'Expected source is not in review-branch lineage; fail closed'
}
$Dir = Join-Path $env:TEMP ('xauusd-v2-readonly-source-' + [guid]::NewGuid().ToString('N'))
$Zip = Join-Path $Dir 'source.zip'
$Extract = Join-Path $Dir 'source'
New-Item -ItemType Directory -Path $Extract -Force | Out-Null
& git -C $Repo archive --format=zip "--output=$Zip" $PinnedCode
if ($LASTEXITCODE -ne 0) { throw 'Source archive failed' }
Expand-Archive -LiteralPath $Zip -DestinationPath $Extract -Force
Write-Output "V2_SOURCE_SHA=$PinnedCode"
Write-Output "V2_REMOTE_HEAD=$observedHead"
Write-Output 'V2_PROBE_SCOPE=DEMO_READONLY_XAUUSD_ALL_SEVEN_TIMEFRAMES'

# Isolate imports to archived source. The script will not install packages or
# write to MT5. Its first read fails closed unless trading API is DISABLED.
$oldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $Extract 'src'
    & $Python (Join-Path $Extract 'phase0\ops\v2_pr33_readonly_mt5_seven_frames_probe_20261022.py') --confirm-readonly
    if ($LASTEXITCODE -ne 0) { throw 'V2_EXTENDED_DEMO_READONLY_CAPTURE_FAIL_CLOSED' }
    Write-Output 'V2_EXTENDED_DEMO_READONLY_CAPTURE_PASS_NO_ORDER'
}
finally {
    $env:PYTHONPATH = $oldPythonPath
}
