"""No-MT5 tests of immutable R1 failure and owner-gated R2 correction."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "demo_adapter" / "scripts"
SCRIPT = SCRIPTS / "v12-d0-r2-attended-bootstrap.ps1"
MANIFEST = ROOT / (
    "phase0/roadmap/DEMO_V12_D0_R2_SOURCE_SHA256_MANIFEST_2026-10-20.json"
)
R2 = ROOT / (
    "phase0/roadmap/DEMO_V12_D0_R2_FROZEN_REGISTRATION_2026-10-20.json"
)
R1 = ROOT / (
    "phase0/roadmap/DEMO_V12_D0_DIAGNOSTIC_NOT_CAPTURE_FROZEN_REGISTRATION_2026-10-20.json"
)
TEST_HEAD = "3ff100189349ada29331730af99459fecc4ea821"
DIGEST = "f" * 64


def test_no_reserved_powershell_auto_variable_assignment() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for reserved in ("host", "pid", "home", "psversiontable", "error"):
        assert not re.search(
            rf"(?im)^\s*\${reserved}\s*=", text,
        ), reserved
    # The failing original inline command assigned $Host. R2 must not.
    assert "$pythonHostFile =" in text
    assert "$terminalProcessId =" in text


def test_different_immutable_registration_and_one_attempt() -> None:
    a = json.loads(R1.read_text(encoding="utf-8"))
    b = json.loads(R2.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert hashlib.sha256(R1.read_bytes()).hexdigest() == (
        manifest["prior_r1_registration_sha256"]
    )
    assert hashlib.sha256(R2.read_bytes()).hexdigest() == (
        manifest["new_r2_registration_sha256"]
    )
    assert manifest["new_r2_registration_sha256"] != manifest[
        "prior_r1_registration_sha256"
    ]
    assert b["superseded_r1_registration_sha256"] == (
        manifest["prior_r1_registration_sha256"]
    )
    assert b["owner_d0_confirmation"] is None
    assert b["vps_mt5_execution_authorized_in_git"] is False
    assert b["broker_trading_allowed"] is False
    assert b["four_hour_capture_allowed"] is False
    assert b["actual_cost_admission_allowed"] is False
    assert a["one_attempt_per_registration_sha"] is True
    assert b["one_attempt_per_registration_sha"] is True


def test_all_reviewed_source_and_r2_sha256_bytes() -> None:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert doc["status"].startswith("NOT_APPROVED_NOT_EXECUTED")
    assert len(doc["files"]) == 5
    for entry in doc["files"]:
        raw = (ROOT / entry["path"]).read_bytes()
        assert b"\r\n" not in raw, entry["path"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["path"]
    assert doc["r1_owner_approval_does_not_transfer"] is True
    assert doc["r1_reuse_prohibited"] is True
    assert doc["actual_vps_mt5_r2_executed"] is False


def test_bootstrap_no_broker_import_and_no_task_mutation() -> None:
    source = SCRIPT.read_text(encoding="utf-8").lower()
    for forbidden in (
        "import metatrader5", "order_send(", "order_check(",
        "order_calc_margin(", "symbol_select(", "schtasks.exe",
        "register-scheduledtask", "stop-scheduledtask",
        "start-scheduledtask", "set-scheduledtask", "terminal_login(",
        "git pull", "git merge", "git reset --hard",
    ):
        assert forbidden not in source
    assert "if ($shellonlytest)" in source
    assert "new_r2_owner_approval_required" in source  # mandatory rejection without approval
    assert "if (-not $ownerapprovedr2)" in source
    assert "privateevidence" in source
    assert "r2-isolatedstage" in source


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PS5.1 only")
def test_native_windows_ps51_parser_and_execution_of_safe_branch() -> None:
    executable = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    if not executable.is_file():
        pytest.skip("native Windows PowerShell 5.1 absent")
    parser_script = (
        "$errors=$null;$tokens=$null;"
        "[System.Management.Automation.Language.Parser]::ParseFile("
        "'"+str(SCRIPT).replace("'", "''")+"',"
        "[ref]$tokens,[ref]$errors)|Out-Null;"
        "if($errors.Count -gt 0){$errors|Out-String|Write-Host;exit 14};"
        "Write-Host 'R2_PS51_PARSER_PASS'"
    )
    result = subprocess.run(  # noqa: S603 (native Windows PS5.1 exact local binary only)
        [str(executable), "-NoProfile", "-NonInteractive", "-Command", parser_script],
        capture_output=True, text=True, check=False, timeout=25,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run(  # noqa: S603 (native Windows PS5.1 exact local binary only)
        [
            str(executable), "-NoProfile", "-NonInteractive",
            "-File", str(SCRIPT),
            "-ExpectedCommit", TEST_HEAD,
            "-NewRegistrationSHA256",
            json.loads(MANIFEST.read_text())["new_r2_registration_sha256"],
            "-WrapperSHA256", DIGEST,
            "-PythonHostSHA256", DIGEST,
            "-JournalSHA256", DIGEST,
            "-ShellOnlyTest",
        ],
        capture_output=True, text=True, check=False, timeout=25,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "R2_SHELL_PREFLIGHT_PASS_NO_GIT_NO_MT5_NO_EVIDENCE_WRITES" in result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PS5.1 only")
def test_native_windows_ps51_requires_fresh_approval() -> None:
    exe = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    cmd = [
        str(exe), "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
        "-ExpectedCommit", TEST_HEAD,
        "-NewRegistrationSHA256", DIGEST,
        "-WrapperSHA256", DIGEST, "-PythonHostSHA256", DIGEST,
        "-JournalSHA256", DIGEST,
    ]
    result = subprocess.run(  # noqa: S603 (native Windows PS5.1 exact local binary only)
        cmd, capture_output=True, text=True, check=False, timeout=25,
    )
    assert result.returncode != 0
    assert "NEW_R2_OWNER_APPROVAL_REQUIRED" in result.stderr
