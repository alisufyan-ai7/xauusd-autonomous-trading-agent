from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
WINDOWS = ROOT / "deploy" / "windows"


def test_pcr3_host_controls_require_explicit_tokens_and_zero_execution() -> None:
    start = (WINDOWS / "Start-ExecutionDisabledCandidate.ps1").read_text(encoding="utf-8")
    stop = (WINDOWS / "Stop-ExecutionDisabledCandidate.ps1").read_text(encoding="utf-8")
    status = (WINDOWS / "Get-ExecutionDisabledCandidateStatus.ps1").read_text(
        encoding="utf-8"
    )

    assert 'ValidateSet("START-EXECUTION-DISABLED-SHADOW")' in start
    assert 'ValidateSet("STOP-EXECUTION-DISABLED-SHADOW")' in stop
    assert "MetaTrader5 bridge must be exactly 5.0.6090" in start
    assert "--broker-preflight" in start
    assert "--run-service" in start
    assert "execution_enabled = $false" in start
    assert "broker_action_count = 0" in start
    assert "execution_enabled = $false" in stop
    assert "broker_action_count = 0" in stop
    assert "execution_enabled = $false" in status
    assert "broker_action_count = 0" in status


@pytest.mark.skipif(platform.system() != "Windows", reason="PowerShell parser is Windows-only")
def test_pcr3_host_control_scripts_parse_on_native_windows() -> None:
    powershell = shutil.which("powershell.exe")
    assert powershell is not None
    scripts = [
        WINDOWS / "Start-ExecutionDisabledCandidate.ps1",
        WINDOWS / "Stop-ExecutionDisabledCandidate.ps1",
        WINDOWS / "Get-ExecutionDisabledCandidateStatus.ps1",
    ]
    for script in scripts:
        command = (
            "$ErrorActionPreference='Stop';"
            f"$null=[scriptblock]::Create((Get-Content -LiteralPath '{script}' -Raw))"
        )
        completed = subprocess.run(  # noqa: S603 -- executable is resolved from runner PATH
            [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
