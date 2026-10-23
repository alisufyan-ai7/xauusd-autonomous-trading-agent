"""Static and native Windows parse checks for owner-run read-only broker probe."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "phase0/ops/real_exness_demo_broker_money_readonly_pr40_20261023.ps1"
PIN = "dc5bed52682f3ece8ebd1b120bd24723d1f716b8"


def test_readonly_powershell_uses_exact_pinned_pr40_revision():
    content = SCRIPT.read_text(encoding="utf-8")
    assert "$Pinned = '" + PIN + "'" in content
    assert "$Branch = 'integration/real-exness-demo-v2-single-lineage-20261023'" in content
    assert "git -C $Repo merge-base --is-ancestor $Pinned $Fetched" in content
    assert "git -C $Repo archive --format=zip" in content
    assert "git -C $Repo checkout" not in content
    assert "git -C $Repo pull" not in content


def test_powershell_operator_consent_and_readonly_api_surface():
    s = SCRIPT.read_text(encoding="utf-8")
    assert "if (-not $ConfirmRealBrokerReadOnly)" in s
    assert "real_demo_money_readonly.py" in s
    assert "& $Python $Entry --confirm-readonly" in s
    assert "& $Python $Entry --enable-trading" not in s
    assert "order_send(" not in s
    assert "order_check(" not in s
    assert "MT5.login(" not in s
    assert "Register-ScheduledTask" not in s
    assert "Set-ScheduledTask" not in s
    assert "Remove-Item -LiteralPath $Stage" in s


@pytest.mark.skipif(shutil.which("powershell") is None, reason="Windows PowerShell 5.1 unavailable")
def test_native_windows_powershell_parses_attended_broker_probe():
    # PARSE ONLY, never run the VPS script or touch the terminal.
    quoted = str(SCRIPT).replace("'", "''")
    check = (
        "$tokens=$null; $errors=$null; "
        "[System.Management.Automation.Language.Parser]::ParseFile("
        f"'{quoted}',[ref]$tokens,[ref]$errors)|Out-Null; "
        "if($errors.Count -ne 0){$errors|Out-String|Write-Output; exit 1}"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", check],
        capture_output=True, text=True, timeout=35, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
