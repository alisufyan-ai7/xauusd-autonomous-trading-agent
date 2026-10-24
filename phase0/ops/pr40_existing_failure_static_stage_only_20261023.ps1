#requires -Version 5.1
# ONE optional owner-attended short/static read-only diagnosis of the EXISTING
# incomplete broker capture, not another 4h prospective quote collection.
# Does NOT execute order_check/order_send, change MT5 accounts, enable trades,
# register tasks, checkout the VPS worktree, or read prior private raw evidence.
[CmdletBinding()]
param([switch] $ConfirmAttendedStaticReadOnlyDiagnosis)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $ConfirmAttendedStaticReadOnlyDiagnosis) {
    throw 'Exact owner permission for short STATIC-ONLY MT5 read required'
}
$Repo = 'C:\Users\Administrator\Desktop\xauusd-autonomous-trading-agent'
$Branch = 'integration/real-exness-demo-v2-single-lineage-20261023'
# Exact code+test SHA containing sanitized failure_stage and safe_guard_code.
$Pinned = '462ac5e94fbeb656f3415603f12e81fdc3c3bd58'
$Python = 'C:\Program Files\Python312\python.exe'
$Terminal = 'C:\Program Files\MetaTrader 5\terminal64.exe'
if (-not (Test-Path -LiteralPath (Join-Path $Repo '.git'))) {
    throw 'Expected XAUUSD Git worktree missing'
}
$ActualRoot = (& git -C $Repo rev-parse --show-toplevel | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or
    -not [string]::Equals(
        [IO.Path]::GetFullPath($ActualRoot).TrimEnd('\'),
        [IO.Path]::GetFullPath($Repo).TrimEnd('\'),
        [StringComparison]::OrdinalIgnoreCase
    )) { throw 'Repository root mismatch; no fallback' }
if (-not (Test-Path -LiteralPath $Python) -or
    -not (Test-Path -LiteralPath $Terminal)) {
    throw 'Pinned Python3.12 or MT5 terminal path missing'
}
$Version = (& $Python --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $Version -notmatch '^Python 3[.]12([.]|$)') {
    throw 'Expected Python3.12 only'
}
$Terminals = @(Get-Process -Name terminal64 -ErrorAction SilentlyContinue)
if ($Terminals.Count -ne 1 -or
    -not [string]::Equals($Terminals[0].Path, $Terminal,
                         [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Exactly one previously approved MT5 terminal required'
}
$HeadBefore = (& git -C $Repo rev-parse HEAD | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'VPS worktree HEAD unavailable' }
& git -C $Repo fetch --no-tags origin "refs/heads/$Branch"
if ($LASTEXITCODE -ne 0) { throw 'GitHub source fetch failed' }
$Fetched = (& git -C $Repo rev-parse FETCH_HEAD | Out-String).Trim()
& git -C $Repo merge-base --is-ancestor $Pinned $Fetched
if ($LASTEXITCODE -ne 0) { throw 'Pinned source not a PR40 ancestor' }

$Temp = Join-Path $env:TEMP ('xauusd-stage-diagnostic-' + [guid]::NewGuid().ToString('N'))
$Source = Join-Path $Temp 'source'
$Zip = Join-Path $Temp 'source.zip'
$Root = Join-Path $env:LOCALAPPDATA 'XAUUSD-BrokerEvidence'
$RunId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$Output = Join-Path $Root ('static-diagnostic-' + $RunId + '-' + [guid]::NewGuid().ToString('N'))
try {
    New-Item -Path $Source -ItemType Directory -Force | Out-Null
    & git -C $Repo archive --format=zip "--output=$Zip" $Pinned
    if ($LASTEXITCODE -ne 0) { throw 'Git pinned export failed' }
    Expand-Archive -LiteralPath $Zip -DestinationPath $Source -Force
    $Script = Join-Path $Source 'demo_adapter\scripts\mt5_comprehensive_readonly.py'
    if (-not (Test-Path -LiteralPath $Script)) {
        throw 'Pinned collector absent from exact export'
    }
    & $Python -B -I -S $Script --self-check-imports
    if ($LASTEXITCODE -ne 0) {
        throw 'STATIC_DIAGNOSTIC_IMPORT_PREFLIGHT_FAIL_CLOSED_NO_MT5'
    }
    New-Item -Path $Root -ItemType Directory -Force | Out-Null
    Write-Output ('STATIC_ONLY_SOURCE_PIN=' + $Pinned)
    Write-Output ('PRIVATE_LOCAL_STATIC_DIAGNOSTIC_DIR=' + $Output)
    Write-Output 'NO_PROSPECTIVE_4H__NO_ORDER_CHECK_SEND__NO_TRADE_SETTING_CHANGES'
    # Omitting --prospective-four-hours is deliberate. This still reads
    # historical context from MT5 once; it never waits for a four-hour window.
    & $Python -B -I $Script --confirm-owner-readonly --output $Output
    $CollectorExit = $LASTEXITCODE
    $Failure = Join-Path $Output 'failure.json'
    $Summary = Join-Path $Output 'shareable_summary.json'
    if (Test-Path -LiteralPath $Failure -PathType Leaf) {
        Write-Output ('FAILURE_JSON_SHA256=' +
            (Get-FileHash -LiteralPath $Failure -Algorithm SHA256).Hash)
    }
    if (Test-Path -LiteralPath $Summary -PathType Leaf) {
        Write-Output ('SANITIZED_SUMMARY_SHA256=' +
            (Get-FileHash -LiteralPath $Summary -Algorithm SHA256).Hash)
    }
    if ($CollectorExit -ne 0) {
        throw 'STATIC_DIAGNOSTIC_FAIL_CLOSED__REVIEW_SANITIZED_STAGE_NO_RETRY'
    }
    Write-Output 'STATIC_DIAGNOSTIC_DONE_NOT_CALIBRATION_OR_TRADING_ADMISSION'
}
finally {
    $HeadAfter = (& git -C $Repo rev-parse HEAD | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $HeadBefore -cne $HeadAfter) {
        Write-Warning 'Git worktree HEAD changed unexpectedly; owner review required'
    }
    if (Test-Path -LiteralPath $Temp) {
        Remove-Item -LiteralPath $Temp -Recurse -Force -ErrorAction SilentlyContinue
    }
}
