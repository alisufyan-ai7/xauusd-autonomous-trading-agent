#requires -Version 5.1
# One comprehensive 4h Exness MT5 DEMO read-only broker capture.
# NO order_send/order_check/account login/symbol select/setting changes.
[CmdletBinding()]
param([switch] $ConfirmAttendedReadOnlyFourHourCapture)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $ConfirmAttendedReadOnlyFourHourCapture) {
    throw 'Owner confirmation for one attended four-hour read-only run required'
}
$Repo = 'C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent'
$Branch = 'integration/real-exness-demo-v2-single-lineage-20261023'
$Pinned = '15fdb77e354e6048d6614b144ed051bf4fd5e094'
$Python = 'C:\Program Files\Python312\python.exe'
$Terminal = 'C:\Program Files\MetaTrader 5\terminal64.exe'
if (-not (Test-Path -LiteralPath (Join-Path $Repo '.git'))) {
    throw 'Expected exact XAUUSD git worktree not found'
}
$ActualRoot = (& git -C $Repo rev-parse --show-toplevel | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or
    -not [string]::Equals(
        [IO.Path]::GetFullPath($ActualRoot).TrimEnd('\'),
        [IO.Path]::GetFullPath($Repo).TrimEnd('\'),
        [StringComparison]::OrdinalIgnoreCase
    )) { throw 'Git worktree root mismatch; no fallback' }
if (-not (Test-Path -LiteralPath $Python) -or
    -not (Test-Path -LiteralPath $Terminal)) {
    throw 'Expected Python3.12 or existing MT5 terminal path missing'
}
$Version = (& $Python --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $Version -notmatch '^Python 3[.]12([.]|$)') {
    throw 'Only exact Python 3.12 is admitted'
}
$Terminals = @(Get-Process -Name terminal64 -ErrorAction SilentlyContinue)
if ($Terminals.Count -ne 1 -or
    -not [string]::Equals($Terminals[0].Path, $Terminal,
                         [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Exactly one existing approved MT5 terminal is required'
}
# Fetch only object/ref metadata; never checkout/pull the worktree.
& git -C $Repo fetch --no-tags origin "refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'GitHub source fetch failed' }
$Remote = (& git -C $Repo rev-parse FETCH_HEAD | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $Remote -cnotmatch '^[0-9a-f]{40}$') {
    throw 'Fetched ref not verifiable'
}
& git -C $Repo merge-base --is-ancestor $Pinned $Remote
if ($LASTEXITCODE -ne 0) { throw 'Pinned source is not in the PR40 lineage' }
$Temp = Join-Path $env:TEMP ('xauusd-readonly-src-' + [guid]::NewGuid().ToString('N'))
$Source = Join-Path $Temp 'source'
$Zip = Join-Path $Temp 'source.zip'
$PrivateRoot = Join-Path $env:LOCALAPPDATA 'XAUUSD-BrokerEvidence'
$RunId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$PrivateEvidence = Join-Path $PrivateRoot (
    'capture-' + $RunId + '-' + [guid]::NewGuid().ToString('N'))
$HeadBefore = (& git -C $Repo rev-parse HEAD | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Git HEAD unavailable' }
try {
    New-Item -Path $Source -ItemType Directory -Force | Out-Null
    & git -C $Repo archive --format=zip "--output=$Zip" $Pinned
    if ($LASTEXITCODE -ne 0) { throw 'Pinned export failed' }
    Expand-Archive -LiteralPath $Zip -DestinationPath $Source -Force
    $Script = Join-Path $Source 'demo_adapter\scripts\mt5_comprehensive_readonly.py'
    if (-not (Test-Path -LiteralPath $Script)) {
        throw 'Pinned comprehensive MT5 collector missing'
    }
    New-Item -Path $PrivateRoot -ItemType Directory -Force | Out-Null
    Write-Output ('READONLY_SOURCE_PIN=' + $Pinned)
    Write-Output 'REAL_EXNESS_PRO_MT5_DEMO_ACCOUNT__READ_ONLY'
    Write-Output 'ONE_FOUR_HOUR_RUN__5_SECOND_SAMPLES__NO_ORDERS'
    Write-Output ('PRIVATE_LOCAL_EVIDENCE_DIR=' + $PrivateEvidence)
    & $Python -B -I $Script --confirm-owner-readonly --output $PrivateEvidence --prospective-four-hours
    if ($LASTEXITCODE -ne 0) {
        throw 'COMPREHENSIVE_MT5_CAPTURE_FAIL_CLOSED__NO_ORDER'
    }
    $Summary = Join-Path $PrivateEvidence 'shareable_summary.json'
    if (-not (Test-Path -LiteralPath $Summary)) {
        throw 'Sanitized completion report missing'
    }
    Write-Output ('SANITIZED_SUMMARY_SHA256=' +
        (Get-FileHash -LiteralPath $Summary -Algorithm SHA256).Hash)
    Write-Output 'READONLY_EVIDENCE_DONE_NOT_ORDER_ADMISSION'
}
finally {
    $HeadAfter = (& git -C $Repo rev-parse HEAD | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $HeadBefore -cne $HeadAfter) {
        Write-Warning 'Git worktree HEAD changed; owner review required'
    }
    if (Test-Path -LiteralPath $Temp) {
        Remove-Item -LiteralPath $Temp -Recurse -Force -ErrorAction SilentlyContinue
    }
}
