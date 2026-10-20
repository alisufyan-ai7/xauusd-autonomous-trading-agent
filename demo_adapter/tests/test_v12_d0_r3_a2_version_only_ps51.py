"""Offline regression: A1 failed; A2 is distinctly owner gated and quote-free."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "demo_adapter/scripts/v12-d0-r3-a2-version-only-ps51.ps1"
REG = ROOT / (
    "phase0/roadmap/"
    "DEMO_V12_D0_R3_PHASE_A2_PROSPECTIVE_VERSION_ONLY_REGISTRATION_2026-10-20.json"
)
A1 = ROOT / (
    "phase0/roadmap/DEMO_V12_D0_R3_PHASE_A1_OWNER_VPS_FAILURE_2026-10-20.md"
)


def test_a1_is_immutable_failed_version_only_and_a2_not_authorized() -> None:
    r = json.loads(REG.read_text(encoding="utf-8"))
    incident = A1.read_text(encoding="utf-8")
    assert r["a1_owner_approval_consumed"] is True
    assert r["a1_same_approval_rerun_allowed"] is False
    assert r["a1_failure"].startswith("FAIL_CLOSED")
    assert r["status"].startswith("DESIGN_ONLY")
    assert r["a2_owner_approval_received"] is False
    assert r["a2_vps_executed"] is False
    assert r["r3_d0_broker_attempt_consumed"] is False
    assert r["phase_b_import_approved"] is False
    assert r["phase_d_attach_approved"] is False
    assert "NativeCommandError" in incident
    assert 'File "<string>", line 1' in incident
    assert "R3_VERIFIER_SHA256_VERIFIED" in incident


def test_a2_payload_contains_no_quoted_literals_or_mt5_call_path() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert b"\r\n" not in SCRIPT.read_bytes()
    match = re.search(r"(?m)^\$code = '(.*)'$", source)
    assert match is not None
    payload = match.group(1)
    assert payload == (
        "import sys;print(sys.version_info[0],sys.version_info[1],"
        "sys.executable,sep=chr(124))"
    )
    assert '"' not in payload and "'" not in payload
    assert "C:\\Program Files\\Python312\\python.exe" in source
    assert "APPROVE_D0_R3_A2_VERSION_ONLY_ONCE" in source
    assert "R3_A2_NEW_OWNER_APPROVAL_REQUIRED__NOT_EXECUTED" in source
    for bad in (
        "import MetaTrader5", "mt5.initialize(", "mt5.account_info(",
        "mt5.order_send(", "mt5.positions_get(", "mt5.orders_get(",
        "Start-Process", "Invoke-WebRequest", "Invoke-RestMethod",
        "New-Item", "Set-Content", "Out-File", "Remove-Item",
        "Register-ScheduledTask", "Set-ScheduledTask",
    ):
        assert bad.lower() not in source.lower(), bad
    for auto in ("host", "pid", "home", "error"):
        assert not re.search(rf"(?im)^\s*\${auto}\s*=", source), auto


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows PS5.1 only")
def test_ps51_parse_shell_only_and_refuse_without_new_approval() -> None:
    shell = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    assert shell.is_file()
    parser = (
        "$errors=$null;$tokens=$null;"
        "[System.Management.Automation.Language.Parser]::ParseFile("
        "'" + str(SCRIPT).replace("'", "''") + "',"
        "[ref]$tokens,[ref]$errors)|Out-Null;"
        "if($errors.Count -gt 0){$errors|Format-List;exit 18};"
        "'R3_A2_PS51_PARSE_PASS'"
    )
    parsed = subprocess.run(  # noqa: S603 (native PS5.1 offline CI only)
        [str(shell), "-NoProfile", "-NonInteractive", "-Command", parser],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert parsed.returncode == 0, parsed.stdout + parsed.stderr
    shell_only = subprocess.run(  # noqa: S603 (native PS5.1 offline CI only)
        [str(shell), "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
         "-ShellOnlyTest"],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert shell_only.returncode == 0, shell_only.stdout + shell_only.stderr
    assert "R3_A2_SHELL_ONLY_TEST__NO_PYTHON_OR_MT5" in shell_only.stdout
    rejected = subprocess.run(  # noqa: S603 (native PS5.1 offline CI only)
        [str(shell), "-NoProfile", "-NonInteractive", "-File", str(SCRIPT)],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert rejected.returncode != 0
    assert "R3_A2_NEW_OWNER_APPROVAL_REQUIRED__NOT_EXECUTED" in rejected.stderr


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows PS5.1 only")
def test_exact_a2_quote_free_python_c_via_native_ps51_with_ci_interpreter() -> None:
    """Actually test -c native argv on CI Python 3.12; never run owner VPS path."""
    shell = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    payload = re.search(
        r"(?m)^\$code = '(.*)'$", SCRIPT.read_text(encoding="utf-8")
    )
    assert payload is not None
    native = sys.executable.replace("'", "''")
    command = (
        "$ErrorActionPreference='Stop';"
        "$code='" + payload.group(1) + "';"
        "$python='" + native + "';"
        "$out=@(& $python -B -I -c $code 2>&1);"
        "if($LASTEXITCODE -ne 0){throw 'CI_PYTHON_ERROR'};"
        "$out"
    )
    got = subprocess.run(  # noqa: S603 (native PS5.1 offline CI only)
        [str(shell), "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert got.returncode == 0, got.stdout + got.stderr
    lines = [x.strip() for x in got.stdout.splitlines() if x.strip()]
    assert len(lines) == 1, lines
    fields = lines[0].split("|")
    assert len(fields) == 3, lines
    assert fields[0:2] == ["3", "12"]
    assert fields[2].lower() == sys.executable.lower()
