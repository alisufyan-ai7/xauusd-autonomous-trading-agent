"""Offline-only guardrails for the *unapproved* attended demo operator script."""
from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from xauusd_demo.envelope import DemoSafetyError

RUNNER = Path(__file__).resolve().parents[1] / (
    "scripts/apc_demo_canary_attended_operator.py"
)


def test_operator_defaults_to_denial_before_any_mt5_import_or_stage() -> None:
    script = runpy.run_path(str(RUNNER), run_name="offline_only")
    main = script["main"]
    with pytest.raises(DemoSafetyError, match="OWNER_AUTHORIZATION_REQUIRED"):
        main([
            "--mode", "entry", "--activation-id", "DENIED",
            "--expires-utc", "2026-10-20T16:00:00Z",
            "--side", "BUY", "--stop", "1990.00",
        ])


def test_operator_no_live_select_no_auto_loop_or_retry() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    for forbidden in (
        "mt5.login(", "mt5.account_select(", "symbol_select(", "order_send(",
        "subprocess.run(", "Register-ScheduledTask", "Start-ScheduledTask",
        "import MetaTrader5", "while True:", "for signal in",
    ):
        assert forbidden not in source, forbidden
    assert "EXPLICIT_APC_DEMO_CANARY_OWNER_AUTHORIZATION_REQUIRED" in source
    assert "CANARY_DURABLE_ONCE_LEDGER_NOT_STAGED" in source
    assert "CANARY_REQUIRES_SEPARATE_ATTENDED_CLOSE_INVOCATION" in source


def test_operator_is_separate_from_production_sealed_shadow() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "DemoCanaryLifecycle" in source
    assert "DemoControlStore" in source
    assert "CanaryJournal" in source
    assert "C:\\Program Files\\Python312\\python.exe" in source
    assert "C:\\Program Files\\MetaTrader 5\\terminal64.exe" in source
    assert "max_daily_submissions=1" in source


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows PowerShell 5.1 only")
def test_native_ps51_preflight_wrapper_safe_rejection_and_parser() -> None:
    shell = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    wrapper = Path(__file__).resolve().parents[1] / (
        "scripts/apc-demo-canary-readonly-preflight.ps1"
    )
    assert shell.is_file()
    source = wrapper.read_text(encoding="utf-8")
    assert "APC_DEMO_READONLY_MT5_PREFLIGHT_REQUIRES_NEW_OWNER_APPROVAL" in source
    assert "pythonText | & $pythonExe -B -I -" in source
    assert "order_send(" not in source
    parser = (
        "$errors=$null;$tokens=$null;"
        "[System.Management.Automation.Language.Parser]::ParseFile("
        "'" + str(wrapper).replace("'", "''") + "',"
        "[ref]$tokens,[ref]$errors)|Out-Null;"
        "if($errors.Count -gt 0){$errors|Format-List;exit 18};"
        "'PS51_CANARY_PREFLIGHT_PARSE_PASS'"
    )
    parsed = subprocess.run(  # noqa: S603 (reviewed native PS5.1 CI runner only)
        [str(shell), "-NoProfile", "-NonInteractive", "-Command", parser],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert parsed.returncode == 0, parsed.stdout + parsed.stderr
    safe = subprocess.run(  # noqa: S603 (reviewed native PS5.1 CI runner only)
        [str(shell), "-NoProfile", "-NonInteractive", "-File",
         str(wrapper), "-ShellOnlyTest"],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert safe.returncode == 0, safe.stdout + safe.stderr
    assert "SHELL_ONLY_NO_PYTHON_NO_MT5" in safe.stdout
    denied = subprocess.run(  # noqa: S603 (reviewed native PS5.1 CI runner only)
        [str(shell), "-NoProfile", "-NonInteractive", "-File", str(wrapper)],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert denied.returncode != 0
    assert "REQUIRES_NEW_OWNER_APPROVAL" in (denied.stdout + denied.stderr)



@pytest.mark.skipif(sys.platform != "win32", reason="native Windows PowerShell 5.1 only")
def test_native_ps51_piped_python_stdin_execution_without_mt5() -> None:
    """Prove PS5.1 stdin path using CI interpreter, not a VPS or MT5."""
    shell = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    assert shell.is_file()
    python = sys.executable.replace("'", "''")
    script = (
        "$ErrorActionPreference='Stop';"
        "$python='" + python + "';"
        "$source='import sys;print(chr(65)+chr(80)+chr(67)+chr(95)+"
        "chr(83)+chr(84)+chr(68)+chr(73)+chr(78)+chr(95)+chr(79)+chr(75))';"
        "$lines=@($source | & $python -B -I - 2>&1);"
        "if($LASTEXITCODE -ne 0){throw 'PS51_PIPE_PYTHON_FAILED'};"
        "$lines"
    )
    result = subprocess.run(  # noqa: S603 (offline Windows CI only)
        [str(shell), "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "APC_STDIN_OK" in result.stdout
