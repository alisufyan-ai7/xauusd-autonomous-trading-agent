"""D0-R3 prospective owner-phased verifier: offline-only safety tests."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "phase0/roadmap/DEMO_V12_D0_R3_PROSPECTIVE_NONEXECUTABLE_REGISTRATION_2026-10-20.json"
SCRIPT = ROOT / "demo_adapter/scripts/v12-d0-r3-phased-runtime-verifier.ps1"
SURVEY = ROOT / "phase0/roadmap/DEMO_V12_D0_R2_STATIC_VPS_SURVEY_OWNER_REPORTED_2026-10-20.md"
R1_SHA = "ab1c266290f3c38f5b8e08bd44b0b06645c0e496839b7c9fa47fd4581f9d0534"
R2_SHA = "13c1ece5068a18b04512776a7387615c51c7075bd9df850d7e4415f6cd773c61"


def test_new_r3_prospective_registration_never_reuses_failures() -> None:
    data = json.loads(REG.read_text(encoding="utf-8"))
    prior = data["previous_failures_immutable"]
    assert [p["registration_sha256"] for p in prior] == [R1_SHA, R2_SHA]
    assert all(p["retry_allowed"] is False for p in prior)
    assert hashlib.sha256(REG.read_bytes()).hexdigest() not in (R1_SHA, R2_SHA)
    assert data["status"].startswith("DESIGN_ONLY")
    assert data["one_attempt_per_r3_d0_registration_sha"] is True
    assert data["r3_d0_attempt_used"] is False
    for field in (
        "r3_owner_approval_received", "version_only_owner_approval_received",
        "import_only_owner_approval_received", "terminal_only_owner_approval_received",
        "d0_mt5_attachment_owner_approval_received",
        "executable_d0_r3_broker_attach_script_in_this_pr",
        "order_check_order_calc_margin_order_send_allowed", "demo_or_live_trading_authorized",
        "github_pr_merge_authorized", "four_hour_240_min_capture_authorized",
        "pcr3_or_gate0_mutation_authorized",
        "vps_mutation_or_automatic_runtime_execution_authorized",
    ):
        assert data[field] is False, field
    assert data["private_output_dir"] is None


def test_exact_owner_survey_is_registered_as_unverified_runtime_candidate() -> None:
    data = json.loads(REG.read_text(encoding="utf-8"))
    evidence = SURVEY.read_text(encoding="utf-8")
    assert data["survey_sha256"] == (
        "e6095ec5b12a47ea86f6767008027c13e8d0e862ecec50b1a6725024f7c37605"
    )
    assert data["python_candidate_literal"] == r"C:\Program Files\Python312\python.exe"
    assert data["reported_terminal"]["pid"] == 6216
    assert data["reported_terminal"]["exe"] == r"C:\Program Files\MetaTrader 5\terminal64.exe"
    assert data["python_version_3_12_proven"] is False
    assert data["python_metatrader5_import_proven"] is False
    assert data["reported_terminal"]["runtime_still_same_proven"] is False
    assert "OWNER-SUPPLIED" in evidence
    assert "MT5_PACKAGE_DIR=True | MT5_DIST_INFO=True" in evidence
    assert "NO_PYTHON_OR_MT5_EXECUTED" in evidence


def test_phases_are_distinct_and_no_broker_attachment_code_exists() -> None:
    data = json.loads(REG.read_text(encoding="utf-8"))
    phases = data["phases"]
    assert [p["id"] for p in phases] == [
        "A_VERSION_ONLY", "B_IMPORT_ONLY", "C_TERMINAL_ONLY", "D_MT5_ATTACH_INVENTORY"
    ]
    assert all(p["approved"] is False and p["executed"] is False for p in phases)
    source = SCRIPT.read_text(encoding="utf-8")
    assert b"\r\n" not in SCRIPT.read_bytes()
    assert "C:\\Program Files\\Python312\\python.exe" in source
    assert "C:\\Program Files\\MetaTrader 5\\terminal64.exe" in source
    assert "ValidateSet('VERSION_ONLY','IMPORT_ONLY','TERMINAL_ONLY')" in source
    assert "APPROVE_D0_R3_" in source
    assert "-B -I -c" in source
    assert "import MetaTrader5 as mt5" in source  # approved import-only branch, no API calls
    assert "R3_PHASE_SEPARATE_OWNER_APPROVAL_REQUIRED__" in source
    for name in ("host", "pid", "home", "error"):
        assert not re.search(rf"(?im)^\s*\${name}\s*=", source), name
    for forbidden in (
        "mt5.initialize(", "mt5.terminal_info(", "mt5.account_info(",
        "mt5.symbol_info(", "mt5.positions_get(", "mt5.orders_get(",
        "mt5.order_send(", "mt5.order_check(", "mt5.order_calc_margin(",
        "Start-Process", "Invoke-WebRequest", "Invoke-RestMethod",
        "Set-Content", "Out-File", "New-Item", "Remove-Item",
        "Register-ScheduledTask", "Set-ScheduledTask", "git.exe",
    ):
        assert forbidden.lower() not in source.lower(), forbidden


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows PowerShell 5.1 only")
def test_native_ps51_parser_and_each_safe_shell_only_branch() -> None:
    shell = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    assert shell.is_file()
    parser = (
        "$errors=$null;$tokens=$null;"
        "[System.Management.Automation.Language.Parser]::ParseFile("
        "'" + str(SCRIPT).replace("'", "''") + "',"
        "[ref]$tokens,[ref]$errors)|Out-Null;"
        "if($errors.Count -gt 0){$errors|Format-List;exit 18};"
        "'PS51_R3_PARSE_PASS'"
    )
    result = subprocess.run(  # noqa: S603
        [str(shell), "-NoProfile", "-NonInteractive", "-Command", parser],
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for phase in ("VERSION_ONLY", "IMPORT_ONLY", "TERMINAL_ONLY"):
        test = subprocess.run(  # noqa: S603
            [str(shell), "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
             "-Phase", phase, "-ShellOnlyTest"],
            capture_output=True, text=True, check=False, timeout=30,
        )
        assert test.returncode == 0, test.stdout + test.stderr
        assert "R3_SHELL_ONLY_TEST__NO_PYTHON_MT5__PHASE=" + phase in test.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows PowerShell 5.1 only")
def test_native_ps51_all_real_phases_reject_unapproved_invocation() -> None:
    shell = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    for phase in ("VERSION_ONLY", "IMPORT_ONLY", "TERMINAL_ONLY"):
        denied = subprocess.run(  # noqa: S603
            [str(shell), "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
             "-Phase", phase],
            capture_output=True, text=True, check=False, timeout=30,
        )
        assert denied.returncode != 0
        assert "R3_PHASE_SEPARATE_OWNER_APPROVAL_REQUIRED__" + phase in denied.stderr
