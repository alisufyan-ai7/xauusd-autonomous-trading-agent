"""Static + Windows PS5.1 parser checks, no script execution or VPS."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

PS1 = Path(__file__).resolve().parents[1] / "scripts" / "v11-offline-review.ps1"


def test_review_script_can_never_enable_or_access_mt5() -> None:
    source = PS1.read_text(encoding="utf-8")
    assert "#requires -Version 5.1" in source
    # Forbid actual capability-changing commands while permitting literal
    # blocklist strings that the static scanner must search for.
    for forbidden in (
        "Register-ScheduledTask", "New-ScheduledTask", "Start-Process",
        "MT5.initialize(", "git push", "git merge",
        "Invoke-RestMethod", "Invoke-WebRequest",
    ):
        assert forbidden not in source
    assert '"order_send("' in source
    assert '"import MetaTrader5"' in source
    assert "Get-FileHash" in source
    assert "OFFLINE_STATIC_ALLOWLIST_PASS" in source


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell 5.1 parser only")
def test_native_windows_powershell_parser_only() -> None:
    command = (
        "$tokens=$null; $errors=$null; "
        "[System.Management.Automation.Language.Parser]::ParseFile("
        "'" + str(PS1).replace("'", "''") + "', [ref]$tokens,"
        " [ref]$errors) | Out-Null; "
        "if ($errors.Count -gt 0) { $errors | Out-String; exit 1 }"
    )
    completed = subprocess.run(  # noqa: S603
        [str(Path(os.environ["SystemRoot"]) / "System32"
             / "WindowsPowerShell" / "v1.0" / "powershell.exe"),
         "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
