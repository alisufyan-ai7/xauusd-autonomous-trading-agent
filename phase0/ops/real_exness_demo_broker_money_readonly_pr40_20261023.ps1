# SUPERSEDED FOR MT5 DISCOVERY by phase0/ops/pr40_one_comprehensive_mt5_readonly_4h_20261023.ps1
# Retained ONLY for historical compatibility and audit. Do not run multiple capture scripts.
#requires -Version 5.1
# XAUUSD REAL Exness Pro DEMO broker-money source observation only.
# NO actual broker order_check/order_send, no Python trading enablement,
# no login/symbol switch, no scheduled tasks and no working tree checkout.
# Operator-run once, separately authorized by the account owner.
[CmdletBinding()]
param(
    [switch] $ConfirmRealBrokerReadOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $ConfirmRealBrokerReadOnly) {
    throw 'Owner must explicitly specify -ConfirmRealBrokerReadOnly'
}
$Repo = 'C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent'
$Python = 'C:\Program Files\Python312\python.exe'
$Branch = 'integration/real-exness-demo-v2-single-lineage-20261023'
$Pinned = 'dc5bed52682f3ece8ebd1b120bd24723d1f716b8'
if (-not (Test-Path -LiteralPath (Join-Path $Repo '.git'))) {
    throw 'Pinned XAUUSD Git worktree not found; do not use another repo'
}
$Root = (& git -C $Repo rev-parse --show-toplevel | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or
    [IO.Path]::GetFullPath($Root).TrimEnd('\') -ine
    [IO.Path]::GetFullPath($Repo).TrimEnd('\')) {
    throw 'XAUUSD repository worktree root mismatch: fail closed'
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw 'Exact Python312 path missing; do not use system fallback'
}
$Version = (& $Python --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $Version -notmatch '^Python 3[.]12([.]|$)') {
    throw 'Only pinned Python 3.12 source is eligible'
}
& git -C $Repo fetch --no-tags origin "refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'Pinned remote branch fetch failed' }
$Fetched = (& git -C $Repo rev-parse FETCH_HEAD | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $Fetched -notmatch '^[0-9a-f]{40}$') {
    throw 'Invalid fetched source revision'
}
& git -C $Repo merge-base --is-ancestor $Pinned $Fetched
if ($LASTEXITCODE -ne 0) {
    throw 'Exact tested source PIN is not an ancestor of the expected PR40'
}
$Stage = Join-Path $env:TEMP ('xauusd-broker-readonly-' + [guid]::NewGuid().ToString('N'))
$Zip = Join-Path $Stage 'source.zip'
$Source = Join-Path $Stage 'source'
$OriginalPYTHONPATH = $env:PYTHONPATH
try {
    New-Item -ItemType Directory -Path $Stage -Force | Out-Null
    & git -C $Repo archive --format=zip "--output=$Zip" $Pinned
    if ($LASTEXITCODE -ne 0) { throw 'Pinned source ZIP export failed' }
    Expand-Archive -LiteralPath $Zip -DestinationPath $Source -Force
    $Entry = Join-Path $Source 'demo_adapter\scripts\real_demo_money_readonly.py'
    if (-not (Test-Path -LiteralPath $Entry)) {
        throw 'Exact source snapshot lacks broker-money diagnostic'
    }
    $env:PYTHONPATH = Join-Path $Source 'demo_adapter\src'
    Write-Output "READONLY_GITHUB_SOURCE_PIN=$Pinned"
    Write-Output 'READONLY_MODE=REAL_EXNESS_PRO_MT5_DEMO_BROKER_NO_ORDER_API'
    & $Python $Entry --confirm-readonly
    if ($LASTEXITCODE -ne 0) { throw 'BROKER_SOURCE_CAPTURE_FAIL_CLOSED_NO_ORDER' }
    Write-Output 'READONLY_CAPTURE_COMPLETE_NO_TRADING_ADMISSION'
}
finally {
    $env:PYTHONPATH = $OriginalPYTHONPATH
    if (Test-Path -LiteralPath $Stage) {
        Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue
    }
}
