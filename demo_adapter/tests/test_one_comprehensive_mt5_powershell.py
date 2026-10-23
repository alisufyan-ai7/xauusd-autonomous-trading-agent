"""Source-pinned single four-hour VPS launcher stays PowerShell parse-only in CI."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "phase0/ops/pr40_one_comprehensive_mt5_readonly_4h_20261023.ps1"
COLLECTOR = ROOT / "demo_adapter/scripts/mt5_comprehensive_readonly.py"


def test_one_comprehensive_launcher_never_calls_trading_api_or_mutates_terminal():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "mt5_comprehensive_readonly.py" in text
    assert "--prospective-four-hours" in text
    assert "--confirm-owner-readonly" in text
    assert "-ConfirmAttendedReadOnlyFourHourCapture" in text
    assert "git -C $Repo archive --format=zip" in text
    assert "git -C $Repo merge-base --is-ancestor $Pinned $Remote" in text
    assert "read-only" in text.lower()
    for banned in (
        "order_send(", "order_check(", "mt5.login(", "symbol_select(",
        "Enable-Trade", "Register-ScheduledTask", "Set-ScheduledTask",
        "git -C $Repo checkout", "git -C $Repo pull",
    ):
        assert banned not in text
    assert "'integration/real-exness-demo-v2-single-lineage-20261023'" in text
    assert "shareable_summary.json" in text


def test_python_collector_uses_exclusive_private_evidence_and_explicit_allowlist():
    text = COLLECTOR.read_text(encoding="utf-8")
    assert "class MT5ReadOnlySurface:" in text
    assert "FORBIDDEN_METHODS" in text
    assert '"xb"' in text
    assert "prospective_run_registration.json" in text
    assert "past_four_hour_broker_ticks.jsonl" in text
    assert "prospective_broker_ticks.jsonl" in text
    assert "private_v11_quote_proxy" in text
    assert '"official_event_and_session_sha256": None' in text
    assert '"policy_a_execution_admitted": False' in text
    assert "mt5.order_send(" not in text
    assert "mt5.order_check(" not in text


@pytest.mark.skipif(
    shutil.which("powershell") is None,
    reason="Windows PowerShell 5.1 parser unavailable on this runner",
)
def test_windows_powershell_parses_only_without_running_capture():
    powershell = shutil.which("powershell")
    assert powershell is not None
    source = str(LAUNCHER).replace("'", "''")
    parse = (
        "$tokens=$null; $errors=$null; "
        "[System.Management.Automation.Language.Parser]::ParseFile("
        f"'{source}',[ref]$tokens,[ref]$errors)|Out-Null; "
        "if($errors.Count -gt 0){$errors|Out-String|Write-Output; exit 1}"
    )
    result = subprocess.run(  # noqa: S603 -- native parser only, no script execution
        [powershell, "-NoProfile", "-NonInteractive", "-Command", parse],
        capture_output=True, text=True, timeout=45, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
