"""Single attended static-only diagnosis of the existing failed collector.

CI parses source only; it NEVER runs the PowerShell broker script.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "phase0/ops/pr40_existing_failure_static_stage_only_20261023.ps1"


def test_one_static_diagnostic_is_opt_in_readonly_and_no_prospective_run() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "$Pinned = '723e276ca32f80e6b705c8dd087a4325609c59e5'" in source
    assert "$ConfirmAttendedStaticReadOnlyDiagnosis" in source
    assert "& $Python -B -I -S $Script --self-check-imports" in source
    assert "& $Python -B -I $Script --confirm-owner-readonly --output $Output" in source
    assert "NO_PROSPECTIVE_4H" in source
    assert "static-diagnostic-" in source
    assert "failure.json" in source and "shareable_summary.json" in source
    assert "git -C $Repo archive --format=zip" in source
    assert "git -C $Repo merge-base --is-ancestor $Pinned $Fetched" in source
    for prohibited in (
        "order_send(", "order_check(", "mt5.login(",
        "Enable-Trade", "Register-ScheduledTask", "Set-ScheduledTask",
        "git -C $Repo checkout", "git -C $Repo pull",
    ):
        assert prohibited not in source
    # The actual Python invocation has no four-hour prospective option.
    for line in source.splitlines():
        if line.strip().startswith("& $Python -B -I $Script "):
            assert "--prospective-four-hours" not in line


@pytest.mark.skipif(
    shutil.which("powershell") is None,
    reason="Native Windows PowerShell 5.1 parser unavailable",
)
def test_windows_powershell_parses_only() -> None:
    powershell = shutil.which("powershell")
    assert powershell is not None
    escaped = str(SCRIPT).replace("'", "''")
    command = (
        "$tokens=$null; $errors=$null; "
        "[System.Management.Automation.Language.Parser]::ParseFile("
        f"'{escaped}',[ref]$tokens,[ref]$errors)|Out-Null; "
        "if($errors.Count -gt 0){$errors|Out-String|Write-Output; exit 1}"
    )
    result = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, timeout=45, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
