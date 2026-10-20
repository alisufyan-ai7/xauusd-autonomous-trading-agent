"""R2 failed pre-MT5; survey is read-only and NOT another D0 attempt."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SURVEY = ROOT / (
    "demo_adapter/scripts/v12-d0-r2-python-environment-readonly-survey.ps1"
)


def test_survey_never_executes_python_mt5_or_git_or_order_apis() -> None:
    source = SURVEY.read_text(encoding="utf-8")
    assert "D0_PYTHON_LOCATION_SURVEY_END__NO_PYTHON_OR_MT5_EXECUTED" in source
    assert b"\r\n" not in SURVEY.read_bytes()
    assert "Get-Process -Name 'terminal64'" in source
    assert "python.exe" in source
    assert "MetaTrader5" in source  # on-disk package-name check, NOT import
    forbidden = (
        "Import-Module MetaTrader5",
        "import MetaTrader5",
        "Initialize(",
        "order_send",
        "order_check",
        "order_calc_margin",
        "Start-Process",
        "Set-Location",
        "New-Item",
        "Set-Content",
        "Out-File",
        "Add-Content",
        "Remove-Item",
        "Invoke-Expression",
        "Invoke-WebRequest",
        "Invoke-RestMethod",
        "git.exe",
        "schtasks.exe",
        "Register-ScheduledTask",
        "Set-ScheduledTask",
    )
    for command in forbidden:
        assert command.lower() not in source.lower(), command
    assert not re.search(r"(?im)^\s*\$(host|pid|home|error)\s*=", source)


@pytest.mark.skipif(sys.platform != "win32", reason="PS5.1 only on Windows")
def test_native_windows_powershell_parser_and_read_only_execution() -> None:
    shell = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
    assert shell.is_file()
    parser_script = (
        "$errors=$null;$tokens=$null;"
        "[System.Management.Automation.Language.Parser]::ParseFile("
        "'" + str(SURVEY).replace("'", "''") + "',"
        "[ref]$tokens,[ref]$errors)|Out-Null;"
        "if($errors.Count -gt 0){$errors|Format-List;exit 18};"
        "'PS51_SURVEY_PARSE_PASS'"
    )
    parsed = subprocess.run(  # noqa: S603
        [str(shell), "-NoProfile", "-NonInteractive", "-Command", parser_script],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert parsed.returncode == 0, parsed.stdout + parsed.stderr
    executed = subprocess.run(  # noqa: S603
        [str(shell), "-NoProfile", "-NonInteractive", "-File", str(SURVEY)],
        capture_output=True, text=True, check=False, timeout=35,
    )
    assert executed.returncode == 0, executed.stdout + executed.stderr
    assert "D0_PYTHON_LOCATION_SURVEY_START" in executed.stdout
    assert "D0_PYTHON_LOCATION_SURVEY_END__NO_PYTHON_OR_MT5_EXECUTED" in (
        executed.stdout
    )
