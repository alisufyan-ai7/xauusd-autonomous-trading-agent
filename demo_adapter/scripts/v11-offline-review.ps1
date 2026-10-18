#requires -Version 5.1
<#
.SYNOPSIS
  V1.1 OFFLINE CODE REVIEW ONLY. No MT5/VPS capture or deployment.
.DESCRIPTION
  Static capability scan + optional local synthetic-only tests. NO terminal
  connection, scheduler modification, trading enablement, broker calls,
  collector launch, credential loading, or external network work.
  Do not run this file on VPS without separate owner approval, even though it
  does not access MT5. This script is not the live capture-run permission.
#>
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "",
    [switch]$RunSyntheticTests
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) {
    $RepositoryRoot = [IO.Path]::GetFullPath(
        (Join-Path $PSScriptRoot "..\..")
    )
}
$root = [IO.Path]::GetFullPath($RepositoryRoot)
$files = @(
    "demo_adapter\scripts\v11_readonly_collector.py",
    "demo_adapter\scripts\v11_capture_orchestrator.py",
    "demo_adapter\scripts\v11_quote_coverage.py",
    "demo_adapter\scripts\v11_offline_risk_bridge.py",
    "demo_adapter\scripts\v11_windows_mt5_readonly_host.py",
    "demo_adapter\scripts\v11_window_readiness.py",
    "demo_adapter\scripts\v12_option_a_cost_recipe.py",
    "demo_adapter\scripts\v12_option_a_flat_lifecycle.py",
    "demo_adapter\scripts\v12_offline_source_packet.py",
    "demo_adapter\scripts\v12_windows_mt5_readonly_host.py",
    "demo_adapter\scripts\v12_attempt_journal.py",
    "demo_adapter\scripts\v12_journaled_readonly_port.py",
    "demo_adapter\scripts\v11_session_scope_feasibility.py",
    "src\xauusd_agent\risk\full_policy_a.py"
)
$blocked = @(
    "import MetaTrader5", "order_send(", "order_check(",
    "order_calc_margin(", "order_calc_profit(", "subprocess.", "os.system("
)
foreach ($relative in $files) {
    $actual = [IO.Path]::GetFullPath((Join-Path $root $relative))
    if (-not $actual.StartsWith($root + [IO.Path]::DirectorySeparatorChar,
                             [StringComparison]::OrdinalIgnoreCase)) {
        throw "SOURCE_NOT_UNDER_REPOSITORY: $relative"
    }
    if (-not [IO.File]::Exists($actual)) {
        throw "SOURCE_MISSING: $relative"
    }
    $source = [IO.File]::ReadAllText($actual)
    foreach ($token in $blocked) {
        if ($source.IndexOf($token, [StringComparison]::Ordinal) -ge 0) {
            throw "BLOCKED_CAPABILITY_TOKEN: $relative :: $token"
        }
    }
    $digest = (Get-FileHash -LiteralPath $actual -Algorithm SHA256).Hash
    Write-Output ("OFFLINE_SOURCE_SHA256 {0} {1}" -f $relative, $digest)
}
Write-Output "OFFLINE_STATIC_ALLOWLIST_PASS; NO_MT5_RUN_OR_DATA_ADMISSION"
if ($RunSyntheticTests) {
    $python = Join-Path $root ".venv\Scripts\python.exe"
    if (-not [IO.File]::Exists($python)) {
        throw "LOCAL_PYTHON_VENV_MISSING_NO_DOWNLOAD_OR_INSTALL_ATTEMPT"
    }
    $previous = (Get-Location).Path
    try {
        Set-Location (Join-Path $root "demo_adapter")
        $tests = @(
            "tests/test_v11_readonly_collector.py",
            "tests/test_v11_quote_coverage.py",
            "tests/test_v11_capture_orchestrator.py",
            "tests/test_v11_offline_risk_bridge.py",
            "tests/test_v11_tick_protocol.py",
            "tests/test_v11_window_readiness.py",
            "tests/test_v11_session_scope_feasibility.py",
            "tests/test_v12_option_a_cost_recipe.py",
            "tests/test_v12_option_a_flat_lifecycle.py",
            "tests/test_v12_option_a_preregistration.py",
            "tests/test_v12_offline_source_packet.py",
            "tests/test_v12_windows_readonly_capture_preparation.py",
            "tests/test_v12_immutable_attempt_journal.py"
        )
        & $python -m pytest -q $tests
        if ($LASTEXITCODE -ne 0) {
            throw "SYNTHETIC_TESTS_FAILED: $LASTEXITCODE"
        }
        Write-Output "OFFLINE_SYNTHETIC_TESTS_PASS"
    }
    finally {
        Set-Location $previous
    }
}
Write-Output "DONE_OFFLINE_ONLY_NO_VPS_NO_BROKER_NO_MERGE"
