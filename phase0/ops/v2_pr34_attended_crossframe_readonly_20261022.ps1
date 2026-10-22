#requires -Version 5.1
# ATTENDED READ-ONLY seven-frame source parity probe.
# No VPS deployment, MT5 login, terminal settings change, orders, or tasks.
# PREPARED ONLY: owner execution requires deliberate separate action.
$ErrorActionPreference = 'Stop'
$Repo = 'C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent'
$Branch = 'implementation/pro-v2-chronology-replay-event-ledger-20261022'
$PinnedSource = '78b1a3c105bdab50f2b4d46eddc8c915db5dfc96'
$Python = 'C:\Program Files\Python312\python.exe'
if (-not (Test-Path -LiteralPath (Join-Path $Repo '.git'))) {
    throw 'Expected Git worktree missing'
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw 'Exact native Python 3.12 missing'
}
$version = (& $Python -c 'import sys;print(sys.version_info.major*100+sys.version_info.minor)')
if ($LASTEXITCODE -ne 0 -or $version.Trim() -ne '312') {
    throw 'Expected Python 3.12 exactly; fail closed'
}
& git -C $Repo fetch --no-tags origin "refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'Read-only source fetch failed' }
$Remote = (& git -C $Repo rev-parse FETCH_HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect fetched review branch' }
& git -C $Repo merge-base --is-ancestor $PinnedSource $Remote
if ($LASTEXITCODE -ne 0) { throw 'Frozen code is not an ancestor of review branch' }

$Temp = Join-Path $env:TEMP ('xauusd-v2-session-probe-' + [guid]::NewGuid().ToString('N'))
$Archive = Join-Path $Temp 'source.zip'
$Extract = Join-Path $Temp 'source'
New-Item -ItemType Directory -Force -Path $Extract | Out-Null
& git -C $Repo archive --format=zip "--output=$Archive" $PinnedSource
if ($LASTEXITCODE -ne 0) { throw 'Pinned Git export failed' }
Expand-Archive -LiteralPath $Archive -DestinationPath $Extract -Force

Write-Output "V2_PR34_READONLY_SOURCE_SHA=$PinnedSource"
Write-Output 'V2_PR34_READONLY_ACCOUNT_MODE=EXNESS_DEMO_PYTHON_TRADING_DISABLED'
$oldPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $Extract 'src'
    & $Python (Join-Path $Extract 'phase0\ops\v2_pr34_attended_crossframe_readonly_20261022.py') --confirm-readonly
    if ($LASTEXITCODE -ne 0) { throw 'V2_PR34_CROSSFRAME_READONLY_DIAGNOSTIC_FAIL_CLOSED' }
    Write-Output 'V2_PR34_CROSSFRAME_READONLY_DIAGNOSTIC_COMPLETE_NO_ORDERS'
}
finally {
    $env:PYTHONPATH = $oldPath
}
