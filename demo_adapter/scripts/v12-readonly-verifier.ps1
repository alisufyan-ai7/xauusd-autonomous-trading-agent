#requires -Version 5.1
<#
  INDEPENDENT READ-ONLY evidence integrity check. Does not call MT5 or network.
  Never certifies actual Exness/source origin, calibrated USD costs or a permit.
  Run only with separately approved private evidence scope.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RegistrationPath,
    [Parameter(Mandatory=$true)][string]$RegistrationSHA256,
    [Parameter(Mandatory=$true)][string]$ExpectedCollectorSHA256,
    [Parameter(Mandatory=$true)][string]$ExpectedVerifierSHA256,
    [Parameter(Mandatory=$true)][string]$ExpectedHostSHA256,
    [Parameter(Mandatory=$true)][string]$PrivateRawPath,
    [Parameter(Mandatory=$true)][string]$ExpectedRawSHA256
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Assert-Pinned([string]$Path,[string]$Expected,[string]$Label) {
    if (-not [IO.File]::Exists($Path) -or
        $Expected -cnotmatch '^[a-f0-9]{64}$') {
        throw "MISSING_PIN_OR_FILE $Label"
    }
    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -cne $Expected) {
        throw "HASH_MISMATCH $Label"
    }
}
function Read-UTC([string]$Text,[string]$Label) {
    if ($Text -cnotmatch '(Z|\+00:00)$') { throw "NOT_EXPLICIT_UTC $Label" }
    return [DateTimeOffset]::Parse(
        $Text,[Globalization.CultureInfo]::InvariantCulture,
        [Globalization.DateTimeStyles]::AssumeUniversal
    ).ToUniversalTime()
}
$script = [IO.Path]::GetFullPath($MyInvocation.MyCommand.Path)
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
Assert-Pinned $script $ExpectedVerifierSHA256 "REVIEWED_VERIFIER"
Assert-Pinned (Join-Path $PSScriptRoot "v12-readonly-collector.ps1") $ExpectedCollectorSHA256 "REVIEWED_COLLECTOR"
Assert-Pinned (Join-Path $PSScriptRoot "v12_windows_mt5_readonly_host.py") $ExpectedHostSHA256 "REVIEWED_HOST"
Assert-Pinned $RegistrationPath $RegistrationSHA256 "APPROVED_REGISTRATION"
Assert-Pinned $PrivateRawPath $ExpectedRawSHA256 "PRIVATE_BROKER_RAW_EVIDENCE"
if ([IO.Path]::GetFullPath($PrivateRawPath).StartsWith(
    $root + [IO.Path]::DirectorySeparatorChar,
    [StringComparison]::OrdinalIgnoreCase)) {
    throw "PRIVATE_EVIDENCE_IN_GITHUB_WORKTREE"
}
$r = Get-Content -LiteralPath $RegistrationPath -Raw -Encoding UTF8 | ConvertFrom-Json
$e = Get-Content -LiteralPath $PrivateRawPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($r.approved_pr13_design_sha -cne "847829378956670e8936bf46c82e685de41145fd" -or
    $r.approved_pr14_evidence_sha -cne "9d768fcfd160b3ccfc92ecef44fe040da6b77db6" -or
    $r.collector_ps_sha256 -cne $ExpectedCollectorSHA256 -or
    $r.verifier_ps_sha256 -cne $ExpectedVerifierSHA256 -or
    $e.registration_sha256 -cne $RegistrationSHA256 -or
    $e.host_sha256 -cne $ExpectedHostSHA256) {
    throw "LINEAGE_OR_FROZEN_REVIEW_SOURCE_MISMATCH"
}
if ($e.status -cne "RAW_PRIVATE_READ_ONLY_NOT_CALIBRATION_OR_EXECUTION" -or
    $e.numeric_costs_admitted -ne $false -or
    $e.actual_execution_slippage_measured -ne $false -or
    [int]$e.order_actions -ne 0) {
    throw "MISLABELED_RAW_DATA_OR_UNSUPPORTED_EXECUTION_ASSERTION"
}
$start = Read-UTC $r.exact_window_start_utc "RUN_START"
$end = Read-UTC $r.exact_window_end_utc "RUN_END"
$ovStart = Read-UTC $r.v12_overlap_start_utc "OVERLAP_START"
$ovEnd = Read-UTC $r.v12_overlap_end_utc "OVERLAP_END"
if (($end-$start).TotalMinutes -ne 240 -or
    $ovStart -lt $start -or $ovEnd -gt $end -or $ovStart -ge $ovEnd) {
    throw "MISMATCHED_FOUR_HOUR_REGISTRATION"
}
if ((Read-UTC $e.window_start_utc "EVIDENCE_START") -ne $start -or
    (Read-UTC $e.window_end_utc "EVIDENCE_END") -ne $end -or
    (Read-UTC $e.v12_overlap_start_utc "EVIDENCE_OVERLAP_START") -ne $ovStart -or
    (Read-UTC $e.v12_overlap_end_utc "EVIDENCE_OVERLAP_END") -ne $ovEnd) {
    throw "EVIDENCE_WINDOW_DOES_NOT_MATCH_FROZEN_RUN"
}
if (@($e.polls).Count -ne 2880 -or @($e.ticks).Count -le 0) {
    throw "RAW_POLL_OR_TICK_RECORDS_INCOMPLETE"
}
if ($e.coverage.distinct_poll_slots -ne 2880 -or
    $e.coverage.eligible_minute_bins -ne 240 -or
    $e.coverage.status -cne "QUOTE_ONLY_EVIDENCE_NOT_CALIBRATION_ADMITTED") {
    throw "CAPTURE_COVERAGE_NOT_PROVEN"
}
foreach ($item in @($e.account_before,$e.account_after)) {
    if ($item.demo_identity_sha256 -cne
        "9fed7cb1789aad5b0bb3593f624502263875a55235c013fb5abc00917fa22e91" -or
        $item.external_python_trading_disabled -ne $true -or
        $item.connected -ne $true -or $item.symbol -cne "XAUUSD") {
        throw "READ_ONLY_ACCOUNT_SCOPE_OR_TERMINAL_STATE_UNVERIFIED"
    }
}
foreach ($row in @($e.ticks)) {
    if ($null -eq $row.flags -or $null -eq $row.source_ordinal -or
        [long]$row.timestamp_ms -lt $start.ToUnixTimeMilliseconds() -or
        [long]$row.timestamp_ms -ge $end.ToUnixTimeMilliseconds()) {
        throw "RAW_TICK_FLAGS_ORDER_OR_UTC_BOUNDARY_INVALID"
    }
}
# No uploaded source is authentic merely because the record and hash agree.
Write-Output ("PRIVATE_RAW_SHA256_VERIFIED={0}" -f $ExpectedRawSHA256)
Write-Output ("TICKS_RETAINED={0} POLLS_RETAINED={1}" -f @($e.ticks).Count,@($e.polls).Count)
Write-Output "INTEGRITY_ONLY_PASS__SOURCE_ORIGIN_AND_COST_CALIBRATION_NOT_ADMITTED"
Write-Output "NO_CAPTURE_PERMISSION__NO_DEMO_ORDER_AUTHORITY"
