#requires -Version 5.1
# Single attended staging + REAL BROKER CASH-RECEIPT capture on Exness Pro DEMO.
# NO order_check, order_send, Python-trading toggle or scheduled task changes.
$ErrorActionPreference = 'Stop'
$Repo = 'C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent'
$Branch = 'implementation/v2-demo-authenticated-broker-risk-receipt-20261022'
$Pinned = '414f6d1fd339dd6466b793adf2bd87f328804425'
$Python = 'C:\Program Files\Python312\python.exe'
if (-not (Test-Path -LiteralPath (Join-Path $Repo '.git'))) {
    throw 'Expected XAUUSD git worktree not found'
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw 'Python312 missing: do not downgrade runtime'
}
# Never pass a Python -c expression through PowerShell 5.1 native quoting.
# PowerShell 5.1 strips inner quote marks and makes a valid expression invalid.
$Ver = (& $Python --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $Ver -notmatch '^Python 3[.]12([.]|$)') {
    throw 'Only Python 3.12 is admitted'
}
& git -C $Repo fetch --no-tags origin "refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
$Remote = (& git -C $Repo rev-parse FETCH_HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Git fetched ref unreadable' }
& git -C $Repo merge-base --is-ancestor $Pinned $Remote
if ($LASTEXITCODE -ne 0) { throw 'Exact broker receipt source not in expected GitHub lineage' }
$Temp = Join-Path $env:TEMP ('xauusd-demo-money-' + [guid]::NewGuid().ToString('N'))
$Extract = Join-Path $Temp 'source'
New-Item -ItemType Directory -Path $Extract -Force | Out-Null
$Zip = Join-Path $Temp 'source.zip'
& git -C $Repo archive --format=zip "--output=$Zip" $Pinned
if ($LASTEXITCODE -ne 0) { throw 'Immutable source export failed' }
Expand-Archive -LiteralPath $Zip -DestinationPath $Extract -Force
Write-Output "V2_REAL_DEMO_MONEY_PINNED_SOURCE=$Pinned"
Write-Output 'V2_MODE=EXNESS_PRO_DEMO_READONLY_BROKER_CASH_NOT_A_TRADE'
$Old = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $Extract 'demo_adapter\src'
    & $Python (Join-Path $Extract 'demo_adapter\scripts\real_demo_money_readonly.py') --confirm-readonly
    if ($LASTEXITCODE -ne 0) {
        throw 'REAL_DEMO_BROKER_MONEY_CAPTURE_FAIL_CLOSED_NO_ORDER'
    }
    Write-Output 'V2_BROKER_MONEY_CAPTURE_PASS_REAL_BROKER_NO_ORDER'
}
finally {
    $env:PYTHONPATH = $Old
}
