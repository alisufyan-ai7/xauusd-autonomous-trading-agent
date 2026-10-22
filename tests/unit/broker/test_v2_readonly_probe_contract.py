"""Safe smoke tests for the standalone *read-only* VPS diagnostic script."""

from __future__ import annotations

import ast
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

PROBE = (
    Path(__file__).resolve().parents[3]
    / "phase0/ops/v2_pr33_readonly_mt5_seven_frames_probe_20261022.py"
)


def _load() -> dict[str, object]:
    return runpy.run_path(str(PROBE), run_name="v2_broker_probe_library_no_main")


def test_probe_source_parses_and_has_no_mt5_order_mutation_calls() -> None:
    parsed = ast.parse(PROBE.read_text(encoding="utf-8"))
    forbidden = {
        "order_send", "order_check", "positions_close", "terminal_set",
        "login", "symbol_select",
    }
    invoked = {
        node.func.attr
        for node in ast.walk(parsed)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not forbidden.intersection(invoked)


def test_probe_requires_explicit_readonly_flag(
    monkeypatch, capsys,
) -> None:
    data = _load()
    monkeypatch.setattr(sys, "argv", ["test-probe"])
    assert data["main"]() == 2
    assert "NOT_EXECUTED_REQUIRE_CONFIRM_READONLY" in capsys.readouterr().out


def test_probe_reports_synthetic_history_shortfall_as_failure(
    monkeypatch, capsys,
) -> None:
    data = _load()
    main = data["main"]
    assert callable(main)
    main.__globals__["capture"] = lambda: {
        "status": "READ_ONLY_HISTORY_SHORTFALL_FAIL_CLOSED",
        "all_requested_history_available": False,
        "order_api_calls": 0,
    }
    monkeypatch.setattr(sys, "argv", ["test-probe", "--confirm-readonly"])
    assert main() == 1
    output = capsys.readouterr().out
    assert "READ_ONLY_HISTORY_SHORTFALL_FAIL_CLOSED" in output
    assert "order_api_calls" in output



@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell 5.1 parser is Windows-only")
def test_attended_readonly_powershell_wrapper_syntax() -> None:
    script = (
        Path(__file__).resolve().parents[3]
        / "phase0/ops/v2_pr33_attended_readonly_mt5_probe_20261022.ps1"
    )
    path = str(script).replace("'", "''")
    parse = (
        "$tokens = $null; $errorsFound = $null; "
        "$null = [System.Management.Automation.Language.Parser]::ParseFile("
        f"'{path}', [ref]$tokens, [ref]$errorsFound); "
        "if ($errorsFound.Count -ne 0) {"
        " $errorsFound | Out-String | Write-Error; exit 1 }"
    )
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", parse],
        capture_output=True, text=True, check=True,
    )
