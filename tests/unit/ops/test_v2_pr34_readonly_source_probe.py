from __future__ import annotations

import ast
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PYTHON_PROBE = ROOT / "phase0/ops/v2_pr34_attended_crossframe_readonly_20261022.py"
POWERSHELL_PROBE = ROOT / "phase0/ops/v2_pr34_attended_crossframe_readonly_20261022.ps1"


def test_source_has_no_broker_order_settings_or_account_login_calls():
    tree = ast.parse(PYTHON_PROBE.read_text(encoding="utf-8"))
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not calls.intersection({
        "order_send", "order_check", "order_calc_margin",
        "order_calc_profit", "login", "symbol_select", "terminal_set",
    })


def test_probe_requires_explicit_attended_readonly_flag(monkeypatch, capsys):
    obj = runpy.run_path(str(PYTHON_PROBE), run_name="read_only_probe_import")
    monkeypatch.setattr(sys, "argv", ["pr34-probe"])
    assert obj["main"]() == 2
    assert "NOT_EXECUTED_REQUIRE_CONFIRM_READONLY" in capsys.readouterr().out


def test_synthetic_crossframe_fail_code_is_not_a_trade_pass(monkeypatch, capsys):
    obj = runpy.run_path(str(PYTHON_PROBE), run_name="read_only_probe_import")
    main = obj["main"]
    main.__globals__["inspect_readonly_crossframe"] = lambda: {
        "status": "READ_ONLY_CROSSFRAME_OR_HISTORY_REJECTED",
        "execution_permitted": False,
        "order_api_calls": 0,
    }
    monkeypatch.setattr(sys, "argv", ["pr34-probe", "--confirm-readonly"])
    assert main() == 1
    assert "READ_ONLY_CROSSFRAME_OR_HISTORY_REJECTED" in capsys.readouterr().out


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
def test_attended_powershell_script_parses_but_is_not_executed():
    fixed = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    path = str(POWERSHELL_PROBE).replace("'", "''")
    code = (
        "$tokens = $null; $errorsFound = $null; "
        "$null = [System.Management.Automation.Language.Parser]::ParseFile("
        f"'{path}', [ref]$tokens, [ref]$errorsFound); "
        "if ($errorsFound.Count -ne 0) { exit 1 }"
    )
    subprocess.run(  # noqa: S603
        [fixed, "-NoProfile", "-NonInteractive", "-Command", code],
        capture_output=True, text=True, check=True,
    )
